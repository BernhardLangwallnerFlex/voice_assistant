#!/usr/bin/env bash
set -euo pipefail

ACR_NAME="flexvoiceassistantacr"
ACR_LOGIN_SERVER="flexvoiceassistantacr.azurecr.io"
IMAGE_NAME="voice-assistant"
RESOURCE_GROUP="rg-voice-assistant"
CONTAINER_APP_NAME="voice-assistant"
APP_URL="https://voice-assistant.livelyplant-1884f397.germanywestcentral.azurecontainerapps.io"

# --- 1. Run tests ---
echo "==> Running tests..."
uv run pytest tests/ -v
echo ""

# --- 2. Commit and push ---
if [ -z "$(git status --porcelain)" ]; then
    echo "==> No changes to commit, deploying current HEAD."
else
    COMMIT_MSG="${1:-}"
    if [ -z "$COMMIT_MSG" ]; then
        read -rp "Commit message: " COMMIT_MSG
    fi
    if [ -z "$COMMIT_MSG" ]; then
        echo "ERROR: Commit message required." >&2
        exit 1
    fi
    git add -A
    git commit -m "$COMMIT_MSG"
fi
git push origin main
echo ""

SHA=$(git rev-parse --short HEAD)
TAG="deploy-${SHA}"
echo "==> Deploying ${TAG}"
echo ""

# --- 3. Build image in ACR ---
echo "==> Building image in ACR..."
az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_NAME}:${TAG}" \
    --file Dockerfile \
    . 2>&1 | tail -5
echo ""

# --- 4. Deploy to Container Apps ---
echo "==> Updating Container App..."
az containerapp update \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${TAG}" \
    -o none
echo ""

# --- 5. Health check ---
echo "==> Waiting for deployment..."
sleep 25
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "${APP_URL}/health" || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "==> Deployed successfully! Health check: 200 OK"
else
    echo "WARNING: Health check returned ${HTTP_STATUS}. Check logs with:"
    echo "  az containerapp logs show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} --type console --tail 30"
fi
echo ""
echo "==> ${APP_URL}"
