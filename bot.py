# imports
import os
import logging
import anthropic
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from google.cloud import datastore
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# load .env for local dev (no-op in Cloud Run)
load_dotenv()

# initialise logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# connect to claude api
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# google cloud datastore client — authenticated automatically on Cloud Run
ds_client = datastore.Client()


# ---- google cloud datastore helpers ----

async def get_history(user_id: int) -> list:
    key = ds_client.key("Conversation", str(user_id))
    entity = ds_client.get(key)
    if entity:
        return entity.get("messages", [])
    return []


async def save_history(user_id: int, messages: list):
    key = ds_client.key("Conversation", str(user_id))
    entity = datastore.Entity(key=key)
    entity["messages"] = messages
    ds_client.put(entity)


async def clear_history(user_id: int):
    key = ds_client.key("Conversation", str(user_id))
    ds_client.delete(key)


# ---- handlers ----

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I am online.")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await clear_history(user_id)
    await update.message.reply_text("🧹 Conversation cleared!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # load history from firestore
    messages = await get_history(user_id)
    messages.append({"role": "user", "content": user_message})

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system="You are an assistant. Try to be as helpful as possible and clear in your responses. Try to keep responses shorter as this is within a texting context.",
            messages=messages
        )

        assistant_message = response.content[0].text
        messages.append({"role": "assistant", "content": assistant_message})

        # persist updated history
        await save_history(user_id, messages)

        # Telegram messages max 4096 chars — split if needed
        if len(assistant_message) > 4096:
            for i in range(0, len(assistant_message), 4096):
                await update.message.reply_text(assistant_message[i:i+4096])
        else:
            await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Error calling Claude: {e}")
        await update.message.reply_text("Something went wrong, please try again.")


# ---- FastAPI web server ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("clear", clear))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.state.bot_app = bot_app

    await bot_app.initialize()

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await bot_app.bot.set_webhook(f"{webhook_url}/webhook")
        logger.info(f"Webhook registered at {webhook_url}/webhook")
    else:
        logger.warning("WEBHOOK_URL not set — webhook not registered.")

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
    data = await request.json()
    update = Update.de_json(data, request.app.state.bot_app.bot)
    await request.app.state.bot_app.process_update(update)
    return Response(status_code=200)


# ---- entrypoint ----

def main():
    if os.getenv("LOCAL_POLLING"):
        # local dev: polling mode
        logger.info("Starting in polling mode (local dev)")
        bot_app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("clear", clear))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        bot_app.run_polling()
    else:
        # Cloud Run / production: web server
        port = int(os.getenv("PORT", 8080))
        logger.info(f"Starting web server on port {port}")
        uvicorn.run(web_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
