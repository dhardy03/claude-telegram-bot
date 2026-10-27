# imports
import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager

import anthropic
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from google.cloud import datastore
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# load .env for local dev (no-op in Cloud Run)
load_dotenv()

# initialise logging (never log message content or keys)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- configuration ----

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
MAX_HISTORY_MESSAGES = 20   # older messages are dropped before each Claude call
MAX_INPUT_CHARS = 4000      # longer user messages are rejected
TELEGRAM_CHUNK = 4096       # Telegram's per-message limit

# Telegram user IDs allowed to use the bot, e.g. "123456,789012".
# Fail closed: if unset, nobody is allowed.
ALLOWED_USER_IDS = {
    int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
}

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_HEADER = "X-Telegram-Bot-Api-Secret-Token"

# connect to claude api (server-side key; see README)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# google cloud datastore client, authenticated automatically on Cloud Run
ds_client = datastore.Client()


# ---- google cloud datastore helpers (blocking calls run in a thread) ----

def _get_history_sync(user_id: int) -> list:
    entity = ds_client.get(ds_client.key("Conversation", str(user_id)))
    return list(entity.get("messages", [])) if entity else []


def _save_history_sync(user_id: int, messages: list):
    entity = datastore.Entity(key=ds_client.key("Conversation", str(user_id)))
    entity["messages"] = messages
    ds_client.put(entity)


def _clear_history_sync(user_id: int):
    ds_client.delete(ds_client.key("Conversation", str(user_id)))


async def get_history(user_id: int) -> list:
    return await asyncio.to_thread(_get_history_sync, user_id)


async def save_history(user_id: int, messages: list):
    await asyncio.to_thread(_save_history_sync, user_id, messages)


async def clear_history(user_id: int):
    await asyncio.to_thread(_clear_history_sync, user_id)


def trim_history(messages: list) -> list:
    """Keep the most recent messages. Claude requires the first message to be from the user."""
    trimmed = messages[-MAX_HISTORY_MESSAGES:]
    while trimmed and trimmed[0]["role"] != "user":
        trimmed = trimmed[1:]
    return trimmed


def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


# ---- handlers ----

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text("Hi! I am online.")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await clear_history(update.effective_user.id)
    await update.message.reply_text("🧹 Conversation cleared!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return  # silently ignore unknown users

    user_message = update.message.text
    if len(user_message) > MAX_INPUT_CHARS:
        await update.message.reply_text(f"Please keep messages under {MAX_INPUT_CHARS} characters.")
        return

    messages = trim_history(await get_history(user_id))
    messages.append({"role": "user", "content": user_message})

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model=MODEL,
            max_tokens=1024,
            system="You are an assistant. Try to be as helpful as possible and clear in your responses. Try to keep responses shorter as this is within a texting context.",
            messages=messages,
        )
        assistant_message = response.content[0].text
    except Exception:
        logger.exception("Error calling Claude")
        await update.message.reply_text("Something went wrong, please try again.")
        return

    # reply first, so a storage error does not hide a successful answer
    for i in range(0, len(assistant_message), TELEGRAM_CHUNK):
        await update.message.reply_text(assistant_message[i:i + TELEGRAM_CHUNK])

    messages.append({"role": "assistant", "content": assistant_message})
    try:
        await save_history(user_id, trim_history(messages))
    except Exception:
        logger.exception("Failed to save conversation history")


# ---- bot construction ----

def build_bot_app():
    bot_app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("clear", clear))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return bot_app


# ---- FastAPI web server ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = build_bot_app()
    app.state.bot_app = bot_app

    await bot_app.initialize()

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await bot_app.bot.set_webhook(
            f"{webhook_url}/webhook",
            secret_token=WEBHOOK_SECRET,
        )
        logger.info("Webhook registered")
    else:
        logger.warning("WEBHOOK_URL not set; webhook not registered.")

    await bot_app.start()
    yield
    await bot_app.stop()
    await bot_app.shutdown()


web_app = FastAPI(lifespan=lifespan)


@web_app.get("/")
async def health_check():
    return {"status": "ok"}


@web_app.post("/webhook")
async def webhook(request: Request):
    # Reject anything that does not carry Telegram's secret token.
    provided = request.headers.get(WEBHOOK_HEADER, "")
    if not WEBHOOK_SECRET or not hmac.compare_digest(provided, WEBHOOK_SECRET):
        return Response(status_code=403)

    data = await request.json()
    update = Update.de_json(data, request.app.state.bot_app.bot)
    await request.app.state.bot_app.process_update(update)
    return Response(status_code=200)


# ---- entrypoint ----

def main():
    if os.getenv("LOCAL_POLLING"):
        logger.info("Starting in polling mode (local dev)")
        build_bot_app().run_polling()
    else:
        if not WEBHOOK_SECRET:
            raise SystemExit("WEBHOOK_SECRET must be set for webhook mode.")
        port = int(os.getenv("PORT", 8080))
        logger.info(f"Starting web server on port {port}")
        uvicorn.run(web_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
