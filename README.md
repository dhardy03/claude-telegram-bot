# Claude Telegram Bot

A Telegram bot and a terminal agent that use the Claude API. The bot stores each user's chat history in Google Cloud Datastore. It runs on Cloud Run and receives messages through a Telegram webhook.

This is a portfolio project. It is not a public service. Running it needs your own Telegram bot, Anthropic API key, and Google Cloud project.

## Technologies

- Python 3.12
- Anthropic Messages API, with tool use
- python-telegram-bot and FastAPI (webhook server)
- Google Cloud Datastore (bot history) and Firestore (CLI history)
- Google Secret Manager and Cloud Run
- Docker
- Rich (terminal output)

## How it works

The Telegram bot sends each message and recent history to Claude and returns the reply. History is limited to the last 20 messages.

The terminal agent runs a tool loop. Claude can read, write, edit, and list files, and run shell commands. Each shell command waits for confirmation before it runs.

The Telegram bot has no tools. Claude can only reply with text.

```
Telegram -> webhook (secret header checked) -> bot.py -> Claude API
                                                  |
                                                  +-> Datastore (history per user)

Terminal -> chat.py -> Claude API <-> tools (files, shell after confirmation)
                |
                +-> Firestore (history per OS user)
```

## Files

| File | Contents |
| --- | --- |
| `bot.py` | Telegram handlers, webhook server, access check, history storage |
| `chat.py` | Terminal agent with file and shell tools |
| `deploy.sh` | Cloud Run deploy script. Reads secrets from Secret Manager. |
| `Dockerfile` | Container image. Includes `bot.py` only. |
| `requirements.txt` | Pinned Python dependencies |
| `setup.py` | Optional console commands |

## Access and limits

- Only Telegram user IDs listed in `ALLOWED_USER_IDS` get replies. If the list is empty, nobody does.
- The webhook rejects requests that lack Telegram's secret token. It refuses to start without `WEBHOOK_SECRET`.
- Messages over 4,000 characters are rejected.
- Secrets are read from Secret Manager at runtime. They are not passed as command-line arguments.

## Run it locally

Requirements: Python 3.12, an Anthropic API key, and a bot token.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # add your values
LOCAL_POLLING=true python bot.py  # Telegram, polling mode
python chat.py                    # terminal agent
```

Set `ALLOWED_USER_IDS` to your Telegram user ID. The bot ignores everyone else. Message @userinfobot to get your ID.

## Deploy to Cloud Run

1. Create the secrets `telegram-token`, `anthropic-api-key`, and `webhook-secret` in Secret Manager. The commands are in the header of `deploy.sh`.
2. Grant the Cloud Run service account the Secret Accessor and Datastore User roles.
3. Run `PROJECT_ID=... WEBHOOK_URL=... ./deploy.sh`. The first deploy creates the service URL, so set `WEBHOOK_URL` on a second deploy.
