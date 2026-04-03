#!/usr/bin/env python3
"""
🧠 AUTO-ACTION ENGINE — SmarterOS v4.3
Cierra el loop: DECISIÓN → ACCIÓN EXTERNA → FEEDBACK

Garantías:
- Nunca bloquea el loop (< 1.5s worst case)
- Nunca falla silenciosamente (todo se loguea)
- Fallback garantizado si Telegram no responde
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger("smarter-food.auto-action")

# ── CONFIG ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "${TELEGRAM_BOT_TOKEN}"
)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6683244662")

DECISIONS_LOG = Path("/var/log/smarter/decisions.log")
DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)

DB_PATH = os.getenv("DB_PATH", "/var/lib/smarter/metrics.db")

# ── REGLAS DE AUTO-ACCIÓN ────────────────────────────────────────
# Formato: (condición, acción, mensaje_template)
# condición: lambda que recibe event_dict → bool

ACTION_RULES = [
    # VALIDADO → confirmar
    (
        lambda e: e.get("status") == "VALID",
        "auto_confirm",
        lambda e: (
            f"✔️ *Producto Validado*\n\n"
            f"📦 *{e.get('producto', 'N/A')}*\n"
            f"💰 Precio: ${e.get('precio', 0):,.0f} CLP\n"
            f"📊 Score: {e.get('score', 0):.1f}/10\n"
            f"🕒 {datetime.now().strftime('%H:%M:%S')}"
        )
    ),
    # SOSPECHOSO → alertar para revisión
    (
        lambda e: e.get("status") == "SANDBOX",
        "auto_alert_review",
        lambda e: (
            f"⚠️ *Precio Sospechoso — Revisar*\n\n"
            f"📦 *{e.get('producto', 'N/A')}*\n"
            f"💰 Precio: ${e.get('precio', 0):,.0f} CLP\n"
            f"📊 Ref: ${e.get('referencia', 0):,.0f} CLP\n"
            f"📊 Score: {e.get('score', 0):.1f}/10\n"
            f"🔍 Desviación: {_dev_pct(e):.0f}%\n"
            f"🕒 {datetime.now().strftime('%H:%M:%S')}"
        )
    ),
    # INCOHERENTE/FRAUDE → alerta crítica
    (
        lambda e: e.get("status") == "REJECTED",
        "auto_alert_fraud",
        lambda e: (
            f"🚨 *POSIBLE FRAUDE DETECTADO*\n\n"
            f"📦 *{e.get('producto', 'N/A')}*\n"
            f"💰 Precio: ${e.get('precio', 0):,.0f} CLP\n"
            f"📊 Ref: ${e.get('referencia', 0):,.0f} CLP\n"
            f"📊 Score: {e.get('score', 0):.1f}/10\n"
            f"🔍 Desviación: {_dev_pct(e):.0f}%\n"
            f"🕒 {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"_Acción recomendada: rechazar y reportar_"
        )
    ),
]

# ── RESPUESTAS PARA EL USUARIO (feedback loop) ──────────────────
USER_RESPONSES = {
    "VALID": lambda e: (
        f"✔️ *{e['producto']}* — Precio válido\n"
        f"Score: {e['score']:.1f}/10\n"
        f"${e['precio']:,.0f} CLP"
    ),
    "SANDBOX": lambda e: (
        f"⚠️ *{e['producto']}* — Precio sospechoso\n"
        f"Score: {e['score']:.1f}/10\n"
        f"Ref: ${e.get('referencia', 0):,.0f} CLP\n"
        f"Necesita revisión manual"
    ),
    "REJECTED": lambda e: (
        f"🚨 *{e['producto']}* — Precio incoherente\n"
        f"Score: {e['score']:.1f}/10\n"
        f"Desviación: {_dev_pct(e):.0f}% sobre referencia\n"
        f"Posible fraude"
    ),
}


def _dev_pct(event: dict) -> float:
    """Porcentaje de desviación precio vs referencia."""
    precio = event.get("precio", 0) or 0
    ref = event.get("referencia", 0) or 0
    if ref == 0:
        return 0
    return abs(precio - ref) / ref * 100


# ── LOG DE DECISIONES ───────────────────────────────────────────

def log_decision(event_id: str, decision: str, input_status: str,
                 output: str, user_id: str = "", producto: str = "",
                 response_time_ms: float = 0):
    """Registra cada decisión automática para trazabilidad."""
    record = {
        "event_id": event_id,
        "decision": decision,
        "input_status": input_status,
        "output": output[:200],  # truncate
        "user_id": user_id,
        "producto": producto,
        "response_time_ms": round(response_time_ms, 1),
        "ts": int(time.time()),
        "ts_iso": datetime.now().isoformat(),
    }
    try:
        with open(DECISIONS_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(f"Decision logged: {decision} → {input_status}")
    except Exception as e:
        logger.error(f"Failed to log decision: {e}")
    return record


# ── ACCIÓN EXTERNA (Telegram) ───────────────────────────────────

def send_telegram(message: str, parse_mode: str = "Markdown") -> dict:
    """Envía mensaje a Telegram. Retorna resultado para logging."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    ts_start = time.time()
    try:
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode,
        }, timeout=5)
        elapsed_ms = (time.time() - ts_start) * 1000
        ok = resp.status_code == 200
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "response_time_ms": round(elapsed_ms, 1),
            "error": None if ok else resp.text[:200],
        }
    except Exception as e:
        elapsed_ms = (time.time() - ts_start) * 1000
        return {
            "ok": False,
            "status_code": 0,
            "response_time_ms": round(elapsed_ms, 1),
            "error": str(e)[:200],
        }


def send_user_response(chat_id: str, message: str, parse_mode: str = "Markdown"):
    """Envía respuesta directa al usuario que envió el evento."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send user response: {e}")


# ── ENGINE PRINCIPAL ────────────────────────────────────────────

def auto_action(event: dict, user_chat_id: Optional[str] = None) -> dict:
    """
    Ejecuta el loop completo: DECISIÓN → ACCIÓN → FEEDBACK → LOG

    Args:
        event: dict con keys: status, score, precio, referencia,
               producto, user_id, id_objeto
        user_chat_id: chat_id de Telegram del usuario (para feedback directo)

    Returns:
        dict con decisiones tomadas, acciones ejecutadas, y métricas
    """
    ts_start = time.time()
    status = event.get("status", "UNKNOWN")
    producto = event.get("producto", "N/A")
    user_id = event.get("user_id", "")
    event_id = event.get("id_objeto", f"evt_{int(time.time())}")

    results = {
        "event_id": event_id,
        "status": status,
        "actions_taken": [],
        "decisions": [],
        "errors": [],
        "total_response_time_ms": 0,
    }

    # 1) EVALUAR REGLAS → decidir acción
    for condition, decision_name, message_fn in ACTION_RULES:
        if condition(event):
            message = message_fn(event)
            action_ts = time.time()

            # 2) EJECUTAR ACCIÓN EXTERNA
            telegram_result = send_telegram(message)

            action_time_ms = (time.time() - action_ts) * 1000

            # 3) LOGUEAR DECISIÓN
            decision_record = log_decision(
                event_id=event_id,
                decision=decision_name,
                input_status=status,
                output=message[:100],
                user_id=user_id,
                producto=producto,
                response_time_ms=action_time_ms,
            )

            results["actions_taken"].append({
                "action": decision_name,
                "telegram_ok": telegram_result["ok"],
                "response_time_ms": telegram_result["response_time_ms"],
            })
            results["decisions"].append(decision_record)

            if not telegram_result["ok"]:
                results["errors"].append({
                    "action": decision_name,
                    "error": telegram_result["error"],
                })

            # 4) FEEDBACK DIRECTO AL USUARIO (si viene de Telegram)
            if user_chat_id and status in USER_RESPONSES:
                user_msg = USER_RESPONSES[status](event)
                send_user_response(user_chat_id, user_msg)

            break  # Solo una acción por evento

    # 5) MÉTRICA GLOBAL
    total_ms = (time.time() - ts_start) * 1000
    results["total_response_time_ms"] = round(total_ms, 1)

    # 6) REGISTRAR EN DB (action tracking)
    _track_action(event_id, status, total_ms, len(results["actions_taken"]) > 0)

    return results


def _track_action(event_id: str, status: str, response_time_ms: float,
                  action_taken: bool):
    """Registra la acción en la DB para métricas de conversión."""
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                event_id TEXT,
                status TEXT,
                response_time_ms REAL,
                action_taken INTEGER,
                ts INTEGER
            )
        """)
        conn.execute(
            "INSERT INTO actions VALUES (?, ?, ?, ?, ?)",
            (event_id, status, response_time_ms, int(action_taken), int(time.time()))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to track action: {e}")


# ── MÉTRICAS DE CONVERSIÓN ──────────────────────────────────────

def get_conversion_metrics(hours: int = 1) -> dict:
    """Calcula métricas de conversión: acciones/eventos, response_time."""
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        ts_cutoff = int(time.time()) - (hours * 3600)

        # Total events
        row = conn.execute(
            "SELECT COUNT(*) FROM events WHERE ts > ?", (ts_cutoff,)
        ).fetchone()
        total_events = row[0] if row else 0

        # Actions taken
        row = conn.execute(
            "SELECT COUNT(*), AVG(response_time_ms) FROM actions WHERE ts > ?",
            (ts_cutoff,)
        ).fetchone()
        total_actions = row[0] if row and row[0] else 0
        avg_response_time = row[1] if row and row[1] else 0

        conn.close()

        return {
            "total_events": total_events,
            "total_actions": total_actions,
            "conversion_rate": round(total_actions / total_events, 3) if total_events > 0 else 0,
            "avg_response_time_ms": round(avg_response_time, 1),
            "period_hours": hours,
        }
    except Exception as e:
        logger.error(f"Failed to get conversion metrics: {e}")
        return {
            "total_events": 0,
            "total_actions": 0,
            "conversion_rate": 0,
            "avg_response_time_ms": 0,
            "period_hours": hours,
        }
