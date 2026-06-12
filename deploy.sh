#!/bin/bash

# Script to deploy Claude Telegram Bot to Google Cloud Run
# Usage: ./deploy.sh <TELEGRAM_TOKEN> <ANTHROPIC_API_KEY> <WEBHOOK_URL>

set -e

# Configuration
PROJECT_ID="aibot-494513"
REGION="europe-west2"
SERVICE_NAME="claude-telegram-bot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <TELEGRAM_TOKEN> <ANTHROPIC_API_KEY> <WEBHOOK_URL>"
    exit 1
fi

TELEGRAM_TOKEN="$1"
ANTHROPIC_API_KEY="$2"
WEBHOOK_URL="$3"

echo "Building and deploying $SERVICE_NAME to Cloud Run..."

# Build the Docker image
echo "Building Docker image..."
docker build -t "${IMAGE_NAME}:latest" .

# Push to Google Container Registry
echo "Pushing image to GCR..."
docker push "${IMAGE_NAME}:latest"

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}:latest" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="TELEGRAM_TOKEN=${TELEGRAM_TOKEN},ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY},WEBHOOK_URL=${WEBHOOK_URL}" \
  --project="${PROJECT_ID}"

echo "Deployment complete!"
