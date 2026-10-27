#!/bin/bash
# Deploy the bot to Google Cloud Run.
#
# Secrets are read from Google Secret Manager; they are never passed as arguments
# or plain environment variables. Create them once before the first deploy:
#
#   printf '%s' "$TELEGRAM_TOKEN"     | gcloud secrets create telegram-token     --data-file=-
#   printf '%s' "$ANTHROPIC_API_KEY"  | gcloud secrets create anthropic-api-key  --data-file=-
#   python -c "import secrets; print(secrets.token_urlsafe(32))" | gcloud secrets create webhook-secret --data-file=-
#
# Usage: PROJECT_ID=my-project REGION=europe-west2 WEBHOOK_URL=https://... ./deploy.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project}"
REGION="${REGION:-europe-west2}"
SERVICE_NAME="${SERVICE_NAME:-claude-telegram-bot}"
WEBHOOK_URL="${WEBHOOK_URL:?Set WEBHOOK_URL to the Cloud Run service URL}"

echo "Deploying $SERVICE_NAME to $PROJECT_ID ($REGION)..."

# --source builds the Dockerfile in this directory with Cloud Build.
# --allow-unauthenticated is required so Telegram can reach the webhook;
# the webhook itself rejects requests without the secret token.
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="WEBHOOK_URL=${WEBHOOK_URL}" \
  --set-secrets="TELEGRAM_TOKEN=telegram-token:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,WEBHOOK_SECRET=webhook-secret:latest"

echo "Deployment complete."
