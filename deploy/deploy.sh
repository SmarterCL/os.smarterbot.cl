#!/bin/bash
# Deploy os.smarterbot.store — v4.3
# Usage: ./deploy/deploy.sh [prod|staging]

set -e

ENV=${1:-prod}
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 SmarterOS Deploy — $ENV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pull latest
cd "$REPO_DIR"
git pull origin main

if [ "$ENV" = "prod" ]; then
    echo ""
    echo "📦 Core services..."
    docker compose up -d --build
    
    echo ""
    echo "🧠 Checking cognitive activation..."
    /usr/local/bin/check_cognitive_activation.sh
    
    echo ""
    echo "🔄 Reloading Caddy..."
    systemctl reload caddy
    
    echo ""
    echo "✅ Deploy complete"
    echo ""
    echo "📊 Service status:"
    docker ps --format "  {{.Names}}: {{.Status}}"
else
    echo "Staging deploy not configured"
fi
