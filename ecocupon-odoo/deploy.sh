#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🚀 ECOCUPON KIOSK — DEPLOYMENT SCRIPT
# Installs and configures the EcoCupon Odoo module
# ═══════════════════════════════════════════════════════════

set -e

ODOO_ADDONS="/opt/smarter-os/addons"
MODULE_NAME="ecocupon_kiosk"
MODULE_SOURCE="/root/ecocupon-odoo-module"

echo "═══════════════════════════════════════════════════════"
echo "  🎫 ECOCUPON KIOSK — INSTALLER"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

ODOO_CONTAINER=$(docker ps --filter "name=odoo" --format "{{.Names}}" 2>/dev/null | head -1)
if [ -z "$ODOO_CONTAINER" ]; then
    echo "⚠️  No Odoo container running. Module will be ready when Odoo starts."
    ODOO_RUNNING=false
else
    echo "✅ Odoo container found: $ODOO_CONTAINER"
    ODOO_RUNNING=true
fi

# 2. Install module
echo ""
echo "📦 Installing module..."
mkdir -p "$ODOO_ADDONS"
if [ -d "$MODULE_SOURCE/$MODULE_NAME" ]; then
    cp -r "$MODULE_SOURCE/$MODULE_NAME" "$ODOO_ADDONS/"
    echo "✅ Module copied to $ODOO_ADDONS/$MODULE_NAME"
else
    echo "❌ Module not found at $MODULE_SOURCE/$MODULE_NAME"
    exit 1
fi

# 3. Set permissions
echo ""
echo "🔧 Setting permissions..."
chown -R 1000:1000 "$ODOO_ADDONS/$MODULE_NAME" 2>/dev/null || true
chmod -R 755 "$ODOO_ADDONS/$MODULE_NAME" 2>/dev/null || true

# 4. Update Odoo if running
if [ "$ODOO_RUNNING" = true ]; then
    echo ""
    echo "🔄 Updating Odoo modules list..."
    docker exec "$ODOO_CONTAINER" python3 -c "
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-u', '$MODULE_NAME', '--stop-after-init'])
" 2>/dev/null && echo "✅ Module updated in Odoo" || echo "⚠️  Manual update needed: Odoo → Apps → Update Apps List"
fi

# 5. n8n workflow import instructions
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  📡 N8N WORKFLOWS — IMPORT INSTRUCTIONS"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "1. Open https://n8n.smarterbot.store"
echo "2. Go to Workflows → Import from File"
echo "3. Import these workflows:"
echo ""
echo "   📁 /root/n8n-workflows/ecocupon-odoo-emdash.json"
echo "      → Bookish search → Emdash generate → Telegram notify"
echo ""
echo "   📁 /root/n8n-workflows/ecu-chat-agent.json"
echo "      → ECU tuning chat agent (detects intent)"
echo ""
echo "   📁 /root/n8n-workflows/ecu-file-upload.json"
echo "      → Receives .bin files → saves → Telegram notify"
echo ""
echo "   📁 /root/n8n-workflows/ecu-purchase.json"
echo "      → Purchase order → Telegram notify"
echo ""
echo "4. Activate each workflow (toggle → Active)"
echo "5. Note the webhook URLs displayed"
echo ""

# 6. Configuration
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ⚙️  CONFIGURATION — ODOO SETTINGS"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "After installing the module:"
echo ""
echo "1. Go to Odoo → Settings → EcoCupon"
echo "2. Configure:"
echo "   - Discount type: Percentage (%) or Fixed (\$)"
echo "   - Discount value: 10 (default)"
echo "   - Validity days: 30 (default)"
echo "   - Enable Emdash (IA): toggle on when cognitive layer is ready"
echo ""
echo "3. Test: Create a sale order → Confirm → See coupon banner"
echo ""

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ ECOCUPON KIOSK — INSTALLATION COMPLETE"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "📁 Module: $ODOO_ADDONS/$MODULE_NAME"
echo "🌐 ECU App: https://ecu.smarterbot.store"
echo "📊 Dashboard: https://bolt.smarterbot.store"
echo "🤖 n8n: https://n8n.smarterbot.store"
echo ""
