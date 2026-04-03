#!/usr/bin/env python3
"""
🧠 COGNITIVE HOOK - SmarterOS v4.3
Hook robusto para capa cognitiva con fallback garantizado + logging
"""

import requests
import logging
from typing import Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/smarter/cognitive_hook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cognitive_hook")

BOOKISH_URL = "http://smarter-bookish:8000"
EMDASH_URL = "http://smarter-emdash:8001"

# Timeouts estrictos para no bloquear el loop
BOOKISH_TIMEOUT = 0.8  # 800ms max
EMDASH_TIMEOUT = 1.2   # 1200ms max

def get_enriched_response(event_data: dict) -> str:
    """
    Obtiene respuesta enriquecida de la capa cognitiva.
    
    Garantías:
    - Nunca bloquea el loop (< 2s worst case)
    - Nunca rompe la API (fallback garantizado)
    - Latencia controlada
    - Logging completo para trazabilidad
    
    Args:
        event_data: Datos del evento a validar
        
    Returns:
        Respuesta enriquecida o fallback
    """
    # Respuesta base SIEMPRE disponible
    base_response = f"Evento validado: Score {event_data.get('score', 0)}"
    
    try:
        logger.info(f"Attempting cognitive enrichment for: {event_data.get('producto', 'unknown')}")
        
        # 1. Intentar pedir contexto a Bookish
        context_response = requests.post(
            f"{BOOKISH_URL}/search",
            json={
                "query": f"{event_data.get('producto', '')} pricing policy",
                "max_results": 3
            },
            timeout=BOOKISH_TIMEOUT
        )
        
        if context_response.status_code != 200:
            logger.warning(f"Bookish returned {context_response.status_code} - using fallback")
            return base_response
        
        context_data = context_response.json()
        logger.info(f"Bookish returned context with {len(context_data.get('results', []))} results")
        
        # 2. Intentar que Emdash redacte
        enriched_response = requests.post(
            f"{EMDASH_URL}/generate",
            json={
                "context": context_data,
                "input": f"Explica validación para {event_data.get('producto', 'producto')}",
                "template": "explicacion_cliente"
            },
            timeout=EMDASH_TIMEOUT
        )
        
        if enriched_response.status_code == 200:
            logger.info("Cognitive enrichment successful")
            return enriched_response.text
        
        logger.warning(f"Emdash returned {enriched_response.status_code} - using fallback")
        
    except requests.exceptions.Timeout as e:
        logger.warning(f"Cognitive layer timeout - using fallback: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Cognitive layer unavailable - using fallback: {e}")
    except Exception as e:
        logger.error(f"Cognitive hook error - using fallback: {e}")
    
    # Fallback: Respuesta lógica del Policy Engine puro
    return base_response

def is_cognitive_layer_available() -> bool:
    """Check if cognitive layer is available"""
    try:
        bookish = requests.get(f"{BOOKISH_URL}/health", timeout=1)
        emdash = requests.get(f"{EMDASH_URL}/health", timeout=1)
        available = bookish.status_code == 200 and emdash.status_code == 200
        logger.info(f"Cognitive layer availability check: {available}")
        return available
    except Exception as e:
        logger.warning(f"Cognitive layer availability check failed: {e}")
        return False

def get_cognitive_status() -> dict:
    """Get detailed cognitive layer status"""
    status = {
        "bookish": {"available": False, "mode": "unknown"},
        "emdash": {"available": False, "mode": "unknown"},
        "ready": False
    }
    
    try:
        bookish = requests.get(f"{BOOKISH_URL}/health", timeout=1)
        if bookish.status_code == 200:
            data = bookish.json()
            status["bookish"] = {
                "available": True,
                "mode": data.get("mode", "unknown"),
                "version": data.get("version", "unknown")
            }
    except:
        pass
    
    try:
        emdash = requests.get(f"{EMDASH_URL}/health", timeout=1)
        if emdash.status_code == 200:
            data = emdash.json()
            status["emdash"] = {
                "available": True,
                "mode": data.get("mode", "unknown"),
                "version": data.get("version", "unknown")
            }
    except:
        pass
    
    status["ready"] = status["bookish"]["available"] and status["emdash"]["available"]
    
    return status

# Endpoint helper for BOLT dashboard
def get_cognitive_activation_status() -> dict:
    """Get activation status for BOLT dashboard"""
    import subprocess
    import sqlite3
    
    DB_PATH = "/var/lib/smarter/metrics.db"
    
    try:
        total = subprocess.run(
            ["sqlite3", DB_PATH, "SELECT COUNT(*) FROM events;"],
            capture_output=True, text=True
        ).stdout.strip()
        
        real = subprocess.run(
            ["sqlite3", DB_PATH, "SELECT COUNT(*) FROM events WHERE user_id NOT IN ('test', 'gemini');"],
            capture_output=True, text=True
        ).stdout.strip()
        
        sandbox_rate = subprocess.run(
            ["sqlite3", DB_PATH, "SELECT ROUND(COUNT(CASE WHEN status='SANDBOX' THEN 1 END)*100.0/COUNT(*), 1) FROM events;"],
            capture_output=True, text=True
        ).stdout.strip()
        
        total = int(total) if total else 0
        real = int(real) if real else 0
        sandbox = float(sandbox_rate) if sandbox_rate else 0.0
        
        conditions_met = 0
        if total >= 200: conditions_met += 1
        if real >= 50: conditions_met += 1
        if 15 <= sandbox <= 45: conditions_met += 1
        
        return {
            "ready": conditions_met == 3,
            "conditions_met": conditions_met,
            "conditions_total": 3,
            "total_events": total,
            "real_events": real,
            "sandbox_rate": sandbox,
            "cognitive_layer": get_cognitive_status()
        }
    except Exception as e:
        return {
            "ready": False,
            "error": str(e),
            "cognitive_layer": get_cognitive_status()
        }
