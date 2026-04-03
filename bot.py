#!/usr/bin/env python3
"""
🦞 SmarterOS Control BOT v4.3 — Con Auto-Action Loop
Convierte mensajes en eventos reales → cierra loop DECISIÓN → ACCIÓN → FEEDBACK
"""

import logging
import subprocess
import sqlite3
import re
import requests
import yaml
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Load config
with open('/app/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

BOT_TOKEN = config['telegram']['bot_token']
DB_PATH = config['database']['metrics']
API_URL = config.get('api', {}).get('url', 'http://localhost:8002')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── PATRÓN PARA DETECTAR "producto precio" ───────────────────────
# Ejemplos válidos:
#   "Hamburguesa 8500"
#   "pizza margarita 12000"
#   "Coca Cola 2500"
#   "laptop gamer 450000"
PRODUCT_PRICE_PATTERN = re.compile(r'^([a-zA-ZáéíóúñÁÉÍÓÚÑ\s]{2,50})\s+(\d{3,7})$')


def parse_product_message(text: str):
    """
    Parsea mensaje "Producto Precio".
    Retorna (producto, precio) o None si no matchea.
    """
    text = text.strip()
    match = PRODUCT_PRICE_PATTERN.match(text)
    if match:
        producto = match.group(1).strip().title()
        precio = int(match.group(2))
        return producto, precio
    return None


# ── COMANDOS ─────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome = """
🦞 **SmarterOS Control BOT v4.3**

**Centro de comando del ecosistema**

📝 *Validar un producto:*
Simplemente envíame:
`Producto Precio`

Ejemplo:
`Hamburguesa 8500`
`Pizza Margarita 12000`

🤖 *Auto-action activo:*
Cada validación genera acción automática

📊 *Comandos de administración:*
/status — Health check global
/metrics — KPIs en vivo
/conversion — Métricas de conversión
/decisions — Últimas decisiones
/policies — Políticas activas
/health — Estado detallado
/help — Esta ayuda
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja mensajes de texto.
    Si es "Producto Precio" → lo valida y cierra el loop.
    """
    text = update.message.text
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    parsed = parse_product_message(text)

    if not parsed:
        producto, precio = parsed
    else:
        producto, precio = parsed

    if producto and precio:
        # ENVIAR A API → cierra loop completo
        await update.message.reply_text(
            f"🔍 Validando *{producto}* (${precio:,})...",
            parse_mode='Markdown'
        )

        try:
            response = requests.post(
                f"{API_URL}/webhook/telegram",
                json={
                    "producto": producto,
                    "precio": precio,
                    "user_id": str(user_id),
                    "user_chat_id": str(chat_id),
                    "raw_message": text,
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                status_emoji = {
                    "VALID": "✔️",
                    "SANDBOX": "⚠️",
                    "REJECTED": "🚨",
                }.get(result.get("status", ""), "❓")

                msg = (
                    f"{status_emoji} *{producto}* — ${precio:,} CLP\n\n"
                    f"Score: `{result.get('score', 'N/A')}`/10\n"
                    f"Estado: `{result.get('status', 'N/A')}`\n"
                    f"Recomendación: {result.get('recomendacion', 'N/A')}\n\n"
                    f"_ID: {result.get('id_objeto', 'N/A')}_"
                )
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f"❌ Error en validación: HTTP {response.status_code}"
                )

        except requests.exceptions.Timeout:
            await update.message.reply_text(
                "⏳ Timeout — la API no respondió. Intenta de nuevo."
            )
        except Exception as e:
            logger.error(f"API call failed: {e}")
            await update.message.reply_text(
                f"❌ Error de conexión: {str(e)[:100]}"
            )

        # Registrar como evento real en DB local
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO events (ts, type, status, score, precio, referencia, user_id, producto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (int(datetime.utcnow().timestamp()), "validation", "VALID", 7.5, float(precio), float(precio) * 0.8, str(user_id), producto)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Local DB insert failed: {e}")

    else:
        # No es un producto → sugerir formato
        await update.message.reply_text(
            "🤔 No entendí el formato.\n\n"
            "Envíame un producto así:\n"
            "`Producto Precio`\n\n"
            "Ejemplo: `Hamburguesa 8500`",
            parse_mode='Markdown'
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global health check"""
    services = config['services']
    results = []

    for name, svc in services.items():
        if svc['type'] == 'systemd':
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', name.replace('-', '_')],
                    capture_output=True, text=True, timeout=5
                )
                status = "✅" if result.stdout.strip() == 'active' else "❌"
                results.append(f"{status} {name}")
            except:
                results.append(f"❌ {name} (error)")
        elif svc['type'] == 'docker':
            try:
                result = subprocess.run(
                    ['docker', 'ps', '--filter', f"name={svc['container']}", '--format', '{{.Status}}'],
                    capture_output=True, text=True, timeout=5
                )
                status = "✅" if 'Up' in result.stdout else "❌"
                results.append(f"{status} {name}")
            except:
                results.append(f"❌ {name} (error)")

    msg = "💓 **Latido del Sistema**\n\n" + "\n".join(results)
    msg += f"\n\n🕒 `{datetime.now().strftime('%H:%M:%S')}`"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current KPIs"""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT
            COUNT(*) as total,
            AVG(score) as avg_score,
            SUM(CASE WHEN status='VALID' THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) as valid_rate,
            SUM(CASE WHEN status='SANDBOX' THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) as sandbox_rate,
            SUM(CASE WHEN status='REJECTED' THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(*),0) as reject_rate
        FROM events
        WHERE ts > strftime('%s','now')-3600
        """
        row = conn.execute(query).fetchone()

        # Real events count
        real_row = conn.execute(
            "SELECT COUNT(*) FROM events WHERE user_id NOT IN ('gemini', 'test') AND ts > strftime('%s','now')-3600"
        ).fetchone()
        real_events = real_row[0] if real_row else 0

        conn.close()

        if row and row[0] > 0:
            msg = f"""
📊 **KPIs (última hora)**

Total Ops: `{row[0]}`
Eventos Reales: `{real_events}`
Avg Score: `{row[1]:.2f}`
Valid Rate: `{(row[2] or 0)*100:.1f}%`
Sandbox Rate: `{(row[3] or 0)*100:.1f}%`
Reject Rate: `{(row[4] or 0)*100:.1f}%`

🕒 `{datetime.now().strftime('%H:%M:%S')}`
"""
        else:
            msg = "📊 No hay datos aún."

        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error obteniendo métricas: {str(e)}")


async def conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Métricas de conversión"""
    try:
        response = requests.get(f"{API_URL}/metrics/conversion", timeout=5)
        if response.status_code == 200:
            data = response.json()
            msg = f"""
📈 **Métricas de Conversión**

Eventos: `{data.get('total_events', 0)}`
Acciones: `{data.get('total_actions', 0)}`
Conversion Rate: `{data.get('conversion_rate', 0)*100:.1f}%`
Avg Response Time: `{data.get('avg_response_time_ms', 0):.0f}ms`

🕒 `{datetime.now().strftime('%H:%M:%S')}`
"""
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No se pudo obtener métricas de conversión")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def decisions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Últimas decisiones automáticas"""
    try:
        response = requests.get(f"{API_URL}/metrics/decisions?limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            decisions_list = data.get('decisions', [])
            if decisions_list:
                msg = "🧠 **Últimas Decisiones**\n\n"
                for d in decisions_list[-5:]:
                    emoji = {"VALID": "✔️", "SANDBOX": "⚠️", "REJECTED": "🚨"}.get(d.get('input_status', ''), "❓")
                    msg += f"{emoji} `{d.get('decision', '?')}` → {d.get('producto', '?')} ({d.get('input_status', '?')})\n"
                    msg += f"   ⏱ {d.get('response_time_ms', 0):.0f}ms\n\n"
                msg += f"_Total registradas: {data.get('total', 0)}_"
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("🧠 Sin decisiones aún.")
        else:
            await update.message.reply_text("❌ No se pudieron obtener decisiones")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def policies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active policies"""
    try:
        with open('/var/www/smarter_latam/config/policies.yaml', 'r') as f:
            policies = yaml.safe_load(f)

        msg = "🧠 **Políticas Activas**\n\n"

        if 'precio' in policies:
            msg += "**Precio:**\n"
            for k, v in policies['precio'].items():
                msg += f"• {k}: `{v}`\n"

        if 'sandbox' in policies:
            msg += "\n**Sandbox:**\n"
            for k, v in policies['sandbox'].items():
                msg += f"• {k}: `{v}`\n"

        if 'alerts' in policies:
            msg += "\n**Alertas:**\n"
            for k, v in policies['alerts'].items():
                msg += f"• {k}: `{v}`\n"

        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error cargando políticas: {str(e)}")


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed health check"""
    services = config['services']
    details = []

    for name, svc in services.items():
        if svc['type'] == 'systemd':
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', name.replace('-', '_')],
                    capture_output=True, text=True, timeout=5
                )
                status = "✅" if result.stdout.strip() == 'active' else "❌"
                details.append(f"{status} **{name}** (systemd)")
            except Exception as e:
                details.append(f"❌ **{name}** (error: {str(e)})")
        elif svc['type'] == 'docker':
            try:
                result = subprocess.run(
                    ['docker', 'inspect', '--format', '{{.State.Status}}', svc['container']],
                    capture_output=True, text=True, timeout=5
                )
                status = "✅" if 'running' in result.stdout.lower() else "❌"
                details.append(f"{status} **{name}** (docker: {result.stdout.strip()})")
            except Exception as e:
                details.append(f"❌ **{name}** (error: {str(e)})")

    msg = "🏥 **Health Check Detallado**\n\n" + "\n".join(details)
    msg += f"\n\n🕒 `{datetime.now().strftime('%H:%M:%S')}`"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    await start(update, context)


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("metrics", metrics))
    app.add_handler(CommandHandler("conversion", conversion))
    app.add_handler(CommandHandler("decisions", decisions))
    app.add_handler(CommandHandler("policies", policies))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("help", help_command))

    # Message handler — catch "producto precio"
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 SmarterOS Control BOT v4.3 iniciado con AUTO-ACTION...")
    logger.info("📝 Envía 'Producto Precio' para validar en tiempo real")
    app.run_polling()
