#!/bin/bash
# ag3ntwerk VPS Quick Setup
# =======================
# Run this on a fresh VPS (Ubuntu 22.04+ / Debian 12+).
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/your-repo/ag3ntwerk/main/deploy/vps/setup.sh | bash
#   # or:
#   bash setup.sh

set -euo pipefail

echo "=================================="
echo "  ag3ntwerk VPS Setup"
echo "=================================="
echo ""

# --- Check prerequisites ---
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# --- Install Docker if not present ---
if ! command -v docker &> /dev/null; then
    echo "[1/5] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "  Docker installed."
else
    echo "[1/5] Docker already installed."
fi

# --- Install Docker Compose plugin if not present ---
if ! docker compose version &> /dev/null; then
    echo "[2/5] Installing Docker Compose plugin..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
    echo "  Docker Compose installed."
else
    echo "[2/5] Docker Compose already installed."
fi

# --- Clone or update the repo ---
INSTALL_DIR="/opt/ag3ntwerk"

if [ -d "$INSTALL_DIR" ]; then
    echo "[3/5] Updating ag3ntwerk..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || echo "  (git pull skipped — not a git repo)"
else
    echo "[3/5] Cloning ag3ntwerk..."
    if [ -n "${AGENTWERK_REPO_URL:-}" ]; then
        git clone "$AGENTWERK_REPO_URL" "$INSTALL_DIR"
    else
        echo "  Set AGENTWERK_REPO_URL or manually clone to $INSTALL_DIR"
        mkdir -p "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

# --- Create .env if it doesn't exist ---
ENV_FILE="deploy/vps/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[4/5] Creating .env from template..."
    cp deploy/vps/.env.example "$ENV_FILE"

    # Generate random passwords
    PG_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
    REDIS_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
    SECRETS_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

    sed -i "s|PG_PASSWORD=change-me-to-a-strong-password|PG_PASSWORD=${PG_PASS}|" "$ENV_FILE"
    sed -i "s|REDIS_PASSWORD=change-me-to-a-strong-password|REDIS_PASSWORD=${REDIS_PASS}|" "$ENV_FILE"
    sed -i "s|AGENTWERK_SECRETS_KEY=change-me-to-a-random-32-char-string|AGENTWERK_SECRETS_KEY=${SECRETS_KEY}|" "$ENV_FILE"

    echo "  .env created with random passwords."
    echo ""
    echo "  IMPORTANT: Edit $INSTALL_DIR/$ENV_FILE to add your API keys."
else
    echo "[4/5] .env already exists, skipping."
fi

# --- Update Caddyfile domain ---
echo "[5/5] Configuration"
echo ""
echo "  Before starting, update these files:"
echo "    1. deploy/vps/Caddyfile — replace 'ag3ntwerk.example.com' with your domain"
echo "    2. deploy/vps/.env      — add your LLM API keys"
echo ""
echo "  Then start ag3ntwerk:"
echo "    cd $INSTALL_DIR"
echo "    docker compose -f deploy/vps/docker-compose.vps.yml --env-file deploy/vps/.env up -d"
echo ""
echo "  To connect your local network (relay agent):"
echo "    1. On your VPS, generate a relay token:"
echo "       curl -X POST https://your-domain/api/v1/fleet/relays/token \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"relay_name\": \"home-lab\", \"created_by\": \"admin\"}'"
echo ""
echo "    2. On your local machine:"
echo "       pip install websockets"
echo "       python scripts/relay-agent.py \\"
echo "         --controller-url wss://your-domain \\"
echo "         --token <token-from-step-1> \\"
echo "         --networks 192.168.1.0/24"
echo ""
echo "=================================="
echo "  Setup complete!"
echo "=================================="
