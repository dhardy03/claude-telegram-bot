# Claude Telegram Bot

A Telegram bot and CLI interface powered by Claude (Anthropic), with conversation history stored in Google Firestore.

## Features

### Telegram Bot (`bot.py`)
- 💬 Chat with Claude via Telegram
- 🧠 Persistent conversation history per user
- 🔄 Supports both webhook (production) and polling (local dev) modes
- 🧹 `/clear` command to reset conversation history
- ☁️ Designed for deployment on Google Cloud Run

### CLI Chat Interface (`chat.py`)
- 🖥️ Interactive PowerShell/terminal chat with Claude
- 🛠️ **Agentic capabilities** - Claude can:
  - 📖 Read files
  - ✏️ Write and edit files
  - 📂 List directories
  - ⚡ Run shell commands (with confirmation)
- 💾 Persistent conversation history in Firestore
- 🎨 Rich terminal UI with markdown rendering
- 📍 Change working directory with `/cd` command

## Installation

### Prerequisites
- Python 3.8+
- Google Cloud account with Firestore enabled
- Anthropic API key
- Telegram Bot Token (for bot.py)

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd claude-telegram-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key
   TELEGRAM_TOKEN=your_telegram_bot_token
   WEBHOOK_URL=https://your-cloud-run-url.com  # for production
   LOCAL_POLLING=true  # for local development
   PORT=8080  # optional, defaults to 8080
   ```

4. **Set up Google Cloud credentials**
   ```bash
   # Set the path to your service account key
   set GOOGLE_APPLICATION_CREDENTIALS=path\to\your\service-account-key.json
   ```

5. **Install as system commands (optional)**
   
   To run the bot from anywhere on your system:
   ```bash
   pip install -e .
   ```
   
   This creates two commands:
   - `claude-bot` - Runs the Telegram bot
   - `R2D2-bot` - Launches the CLI chat interface

## Usage

### Telegram Bot

**Local development (polling mode):**
```bash
python bot.py
# or if installed:
claude-bot
```

**Production (webhook mode):**
Deploy to Google Cloud Run. The bot will automatically set up webhooks.

**Telegram commands:**
- `/start` - Initialize the bot
- `/clear` - Clear conversation history

### CLI Chat Interface

```bash
python chat.py
# or if installed:
R2D2-bot
```

**CLI commands:**
- `/clear` - Clear conversation history
- `/exit` - Quit the chat
- `/help` - Show available commands
- `/cwd` - Show current working directory
- `/cd <path>` - Change working directory

**Example interaction:**
```
You: Can you list the files in this directory?

Claude: [uses list_directory tool]

You: Edit the README.md file and add a new section

Claude: [uses edit_file tool to make changes]
```

## Project Structure

```
claude-telegram-bot/
├── bot.py              # Telegram bot with webhook/polling support
├── chat.py             # CLI chat interface with file system tools
├── requirements.txt    # Python dependencies
├── setup.py           # Package configuration for system-wide commands
├── Dockerfile         # Docker configuration for Cloud Run
├── .env               # Environment variables (not in git)
└── README.md          # This file
```

## Deployment

### Google Cloud Run

1. **Build and deploy:**
   ```bash
   gcloud run deploy claude-telegram-bot \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ANTHROPIC_API_KEY=your_key,TELEGRAM_TOKEN=your_token
   ```

2. **Set the webhook URL:**
   Update your `.env` or Cloud Run environment variables with:
   ```
   WEBHOOK_URL=https://your-service-url.run.app
   ```

### Docker

```bash
docker build -t claude-telegram-bot .
docker run -p 8080:8080 --env-file .env claude-telegram-bot
```

## Architecture

- **Telegram Bot**: Uses FastAPI for webhook handling, `python-telegram-bot` for Telegram API
- **CLI Chat**: Implements an agentic loop with tool use (function calling)
- **Storage**: Google Firestore for conversation persistence
- **AI Model**: Claude Sonnet 4.5 via Anthropic API

## Security Notes

- 🔒 Shell commands in CLI mode require user confirmation before execution
- ⚠️ The CLI tool has file system access - use responsibly

