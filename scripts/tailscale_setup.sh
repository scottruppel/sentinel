#!/usr/bin/env bash
# Sentinel Tailscale setup — run once on the host that serves the Sentinel backend.
# Usage: sudo bash scripts/tailscale_setup.sh

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}[1/4] Installing Tailscale...${NC}"
curl -fsSL https://tailscale.com/install.sh | sh

echo -e "${GREEN}[2/4] Starting Tailscale daemon...${NC}"
systemctl enable --now tailscaled

echo -e "${GREEN}[3/4] Authenticating with Tailscale...${NC}"
echo -e "${YELLOW}A browser window will open (or paste the URL). Log in and approve this device.${NC}"
tailscale up --accept-routes

echo -e "${GREEN}[4/4] Generating Sentinel API key...${NC}"
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

TAILSCALE_IP=$(tailscale ip -4)
TAILSCALE_HOST=$(tailscale status --json 2>/dev/null | python3 -c "
import sys, json
s = json.load(sys.stdin)
me = s.get('Self', {})
print(me.get('DNSName', '').rstrip('.'))
" 2>/dev/null || echo "")

ENV_FILE="$(dirname "$0")/../.env"

echo "" >> "$ENV_FILE"
echo "# --- Tailscale agent access (added by tailscale_setup.sh) ---" >> "$ENV_FILE"
echo "TAILSCALE_ENABLED=true" >> "$ENV_FILE"
echo "SENTINEL_API_KEY=${API_KEY}" >> "$ENV_FILE"

echo ""
echo -e "${GREEN}Done! Share these details with your agent:${NC}"
echo ""
echo "  Tailscale IP   : ${TAILSCALE_IP}"
if [ -n "$TAILSCALE_HOST" ]; then
echo "  MagicDNS host  : ${TAILSCALE_HOST}"
fi
echo "  API base URL   : http://${TAILSCALE_IP}:8000/api"
echo "  Header         : X-API-Key: ${API_KEY}"
echo ""
echo -e "${YELLOW}The API key has been written to .env. Restart the Sentinel backend to pick it up.${NC}"
echo -e "${YELLOW}Also add the agent machine to your Tailscale network (tailscale up on that host).${NC}"
