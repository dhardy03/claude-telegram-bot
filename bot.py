#imports
import os
import logging
import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

#env file
load_dotenv()

#initialise logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#connect to claude api
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

#storing convos
convo_history: dict[int, list] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I am online."
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    convo_history.pop(user_id, None)
    await update.message.reply_text("🧹 Conversation cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Init history for new users
    if user_id not in convo_history:
        convo_history[user_id] = []

    # Append user message
    convo_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system="You are an assistant. Try to be as helpful as possible and clear in your responses.",
            messages=convo_history[user_id]
        )

        assistant_message = response.content[0].text

        # Append assistant response to history
        convo_history[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        # Telegram messages max 4096 chars — split if needed
        if len(assistant_message) > 4096:
            for i in range(0, len(assistant_message), 4096):
                await update.message.reply_text(assistant_message[i:i+4096])
        else:
            await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Error calling Claude: {e}")
        await update.message.reply_text("shits fucked")

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    #commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("AI with the braids")
    app.run_polling()

if __name__ == "__main__":
    main()