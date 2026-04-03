# Smarter Food API — con IA integrada
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Import middleware — contrato de incoherencia (obligatorio)
from api.middleware.incoherencia import ContratoIncoherencia, EstadoValidacion
from api.middleware.mercado import VerificadorMercado, PRECIOS_MERCADO

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "smarter-food.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("smarter-food")

# Event logging — JSON structured for autonomous loop
EVENTS_LOG = Path("/var/log/smarter/events.log")
EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)

def log_event(event: dict):
    """Append structured event to events.log for metrics ingestion."""
    event["ts"] = int(datetime.utcnow().timestamp())
    event["service"] = "smarter-food"
    try:
        with open(EVENTS_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to write event: {e}")

# IA Configuration (prioridad: Ollama local > Gemini > n8n webhook)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.smarterbot.cl/webhook/smarter-food")

# Modo de IA: "ollama" | "gemini" | "n8n" | "mock"
AI_MODE = os.getenv("AI_MODE", "ollama")

# =============================================================================
# MODELOS
# =============================================================================

class ValidacionRequest(BaseModel):
    id_objeto: str
    producto: str
    peso_gramos: Optional[float] = None
    precio: Optional[float] = None
    ubicacion: Optional[str] = ""

class ValidacionResponse(BaseModel):
    id_objeto: str
    producto: str
    score: Optional[float] = None
    recomendacion: str
    observaciones: list[str] = []
    status: str  # "ok" | "pending" | "error"
    ai_mode: str
    timestamp: str

# =============================================================================
# APP
# =============================================================================

app = FastAPI(title="Smarter Food API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# =============================================================================
# MIDDLEWARE — Contrato de Incoherencia
# =============================================================================

contrato = ContratoIncoherencia()
verificador_mercado = VerificadorMercado()

# Contexto del sistema (estado real)
def obtener_contexto() -> dict:
    """Estado real del sistema para verificar coherencia."""
    return {
        "usuarios": {},  # TODO: conectar a DB
        "patrones_fraude": [],  # TODO: cargar desde DB
        "objetos_usuarios": {},  # TODO: tracking de IDs
        "precios_mercado": PRECIOS_MERCADO,
    }

def env_ok() -> bool:
    """Verifica que el nodo tiene sus axiomas configurados."""
    return bool(GEMINI_API_KEY or OLLAMA_URL)

# =============================================================================
# IA ENGINES
# =============================================================================

async def score_with_ollama(data: dict) -> dict:
    """Score con Ollama (Llama 3.2) — local, sin costo"""
    prompt = f"""Eres un experto en calidad alimentaria. Evalúa este producto del 1 al 10.

Producto: {data['producto']}
ID: {data['id_objeto']}
Peso: {data.get('peso_gramos', 'N/A')}g
Precio: ${data.get('precio', 'N/A')} CLP
Ubicación: {data.get('ubicacion', 'N/A')}

Responde SOLO en este formato JSON:
{{
    "score": 8,
    "recomendacion": "Texto breve",
    "observaciones": ["obs1", "obs2"]
}}"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
        )
        resp.raise_for_status()
        result = resp.json()
        return json.loads(result["response"])

async def score_with_gemini(data: dict) -> dict:
    """Score con Gemini 2.0 Flash — rápido y preciso"""
    prompt = f"""Eres un experto en calidad alimentaria. Evalúa este producto del 1 al 10.

Producto: {data['producto']}
ID: {data['id_objeto']}
Peso: {data.get('peso_gramos', 'N/A')}g
Precio: ${data.get('precio', 'N/A')} CLP
Ubicación: {data.get('ubicacion', 'N/A')}

Responde SOLO en este formato JSON:
{{
    "score": 8,
    "recomendacion": "Texto breve",
    "observaciones": ["obs1", "obs2"]
}}"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
        )
        resp.raise_for_status()
        result = resp.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

async def score_with_n8n(data: dict) -> dict:
    """Score vía webhook n8n — orquestación visual"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(N8N_WEBHOOK_URL, json=data)
        resp.raise_for_status()
        return resp.json()

def score_mock(data: dict) -> dict:
    """Mock para testing sin IA"""
    peso = data.get("peso_gramos", 0) or 0
    precio = data.get("precio", 0) or 0

    score = 5.0
    if 150 <= peso <= 350:
        score += 2
    if 1000 <= precio <= 5000:
        score += 1.5
    if data.get("ubicacion"):
        score += 0.5

    score = min(10, max(1, score))

    return {
        "score": round(score, 1),
        "recomendacion": "Producto dentro de parámetros aceptables" if score >= 7 else "Revisar estándares de calidad",
        "observaciones": [
            f"Peso: {peso}g ({'OK' if 150 <= peso <= 350 else 'Fuera de rango'})",
            f"Precio: ${precio} CLP ({'OK' if 1000 <= precio <= 5000 else 'Revisar'})"
        ]
    }

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smarter Food API</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-orange-500 via-red-500 to-pink-600 min-h-screen flex items-center justify-center">
        <div class="text-center text-white">
            <div class="text-6xl mb-4">🍔</div>
            <h1 class="text-4xl font-bold mb-2">Smarter Food API</h1>
            <p class="text-xl opacity-80 mb-6">Nodo de alimentación — Smarter LATAM</p>
            <div class="space-y-2 text-sm">
                <p><a href="/docs" class="underline hover:text-orange-200">📖 API Docs (Swagger)</a></p>
                <p><a href="/validador" class="underline hover:text-orange-200">✅ Validador Universal</a></p>
                <p><a href="/health" class="underline hover:text-orange-200">💚 Health Check</a></p>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "smarter-food",
        "ai_mode": AI_MODE,
        "version": "2.0.0"
    }

@app.get("/validador", response_class=HTMLResponse)
async def validador_ui():
    """Universal validator UI — con IA integrada"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smarter Food — Validador IA</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-orange-500 via-red-500 to-pink-600 min-h-screen flex items-center justify-center p-4">
        <div class="max-w-md w-full">
            <div class="bg-white rounded-3xl shadow-2xl p-8">
                <div class="text-center mb-8">
                    <div class="text-6xl mb-4">🍔</div>
                    <h1 class="text-3xl font-bold text-gray-800 mb-2">Validador con IA</h1>
                    <p class="text-gray-600">Análisis inteligente en 30 segundos</p>
                    <p class="text-xs text-gray-400 mt-2">AI Mode: {AI_MODE}</p>
                </div>

                <form id="validadorForm" class="space-y-4">
                    <div>
                        <input type="text" name="id_objeto" placeholder="#IDOBJETO (QR)" required
                            class="w-full px-5 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-orange-500 transition" />
                    </div>
                    <div>
                        <input type="text" name="producto" placeholder="Producto (ej: Hamburguesa Clásica)" required
                            class="w-full px-5 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-orange-500 transition" />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <input type="number" name="peso_gramos" placeholder="Peso (g)" min="1"
                            class="w-full px-5 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-orange-500 transition" />
                        <input type="number" name="precio" placeholder="Precio (CLP)" min="100"
                            class="w-full px-5 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-orange-500 transition" />
                    </div>
                    <div>
                        <input type="text" name="ubicacion" placeholder="Ubicación (ej: Santiago, CL)"
                            class="w-full px-5 py-4 border-2 border-gray-200 rounded-xl text-lg focus:outline-none focus:border-orange-500 transition" />
                    </div>
                    <button type="submit" id="submitBtn"
                        class="w-full bg-gradient-to-r from-orange-500 to-red-500 text-white py-5 rounded-xl font-bold text-xl hover:shadow-2xl transition transform hover:scale-105 disabled:opacity-50">
                        Validar producto
                    </button>
                </form>

                <div id="statusMessage" class="hidden mt-6 p-4 rounded-xl text-center"></div>
                <div id="resultSection" class="hidden mt-8 pt-8 border-t-2 border-gray-100">
                    <div class="text-center">
                        <div class="text-5xl font-bold mb-2" id="scoreDisplay">--</div>
                        <div class="text-gray-600 mb-4">Score de calidad</div>
                        <div class="bg-gray-50 rounded-xl p-4 mb-4 text-left">
                            <div class="font-bold text-gray-800 mb-2">Recomendación:</div>
                            <div id="recommendationDisplay" class="text-lg">--</div>
                        </div>
                        <div class="bg-gray-50 rounded-xl p-4 mb-6 text-left">
                            <div class="font-bold text-gray-800 mb-2">Observaciones:</div>
                            <ul id="observationsDisplay" class="text-sm text-gray-600 space-y-1">--</ul>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-center mt-6 text-white/80 text-sm">
                Powered by Smarter LATAM — Validador Universal
            </div>
        </div>

        <script>
            document.getElementById("validadorForm").addEventListener("submit", async (e) => {{
                e.preventDefault();
                const form = e.target;
                const submitBtn = document.getElementById("submitBtn");
                const statusMsg = document.getElementById("statusMessage");
                const resultSection = document.getElementById("resultSection");

                submitBtn.disabled = true;
                submitBtn.innerHTML = "⏳ Analizando con IA...";
                statusMsg.className = "hidden";
                resultSection.classList.add("hidden");

                const data = Object.fromEntries(new FormData(form));

                try {{
                    const response = await fetch("/api/validar", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify(data)
                    }});

                    if (!response.ok) throw new Error("Error en el servidor");
                    const result = await response.json();

                    resultSection.classList.remove("hidden");

                    if (result.score) {{
                        document.getElementById("scoreDisplay").textContent = result.score + "/10";
                        document.getElementById("scoreDisplay").className =
                            result.score >= 7 ? "text-5xl font-bold mb-2 text-green-500" :
                            result.score >= 4 ? "text-5xl font-bold mb-2 text-yellow-500" :
                            "text-5xl font-bold mb-2 text-red-500";
                        document.getElementById("recommendationDisplay").textContent = result.recomendacion || "--";
                        if (result.observaciones) {{
                            const list = document.getElementById("observationsDisplay");
                            list.innerHTML = "";
                            (Array.isArray(result.observaciones) ? result.observaciones : [result.observaciones]).forEach(obs => {{
                                const li = document.createElement("li");
                                li.textContent = "• " + obs;
                                list.appendChild(li);
                            }});
                        }}
                    }}

                    statusMsg.className = "mt-6 p-4 rounded-xl text-center bg-green-100 text-green-800";
                    statusMsg.textContent = "✅ Producto analizado correctamente";
                    form.reset();
                }} catch (error) {{
                    statusMsg.className = "mt-6 p-4 rounded-xl text-center bg-red-100 text-red-800";
                    statusMsg.textContent = "❌ Error: " + error.message;
                }} finally {{
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = "Validar otro producto";
                }}
            }});
        </script>
    </body>
    </html>
    """

@app.post("/api/validar", response_model=ValidacionResponse)
async def validar_producto(payload: ValidacionRequest):
    """
    Validación con IA integrada + Contrato de Incoherencia.

    FLUJO:
    1. Contrato de Incoherencia → ¿input coherente?
    2. Si INCOHERENTE → bloqueo inmediato (no llama a IA)
    3. Si SOSPECHOSO → sandbox (precio castigado)
    4. Si VALIDADO → scoring con IA
    """
    logger.info(f"Validación: {payload.producto} (ID: {payload.id_objeto})")

    data = payload.model_dump()
    contexto = obtener_contexto()

    # PASO 1: Contrato de Incoherencia (obligatorio)
    resultado = contrato.evaluar(data, contexto, env_ok())

    # INCOHERENTE → bloqueo inmediato
    if resultado.estado == EstadoValidacion.INCOHERENTE:
        logger.warning(
            f"INCOHERENTE: {payload.id_objeto} — "
            f"score={resultado.score_incoherencia} — {resultado.observaciones}"
        )
        log_event({
            "type": "validation",
            "id_objeto": payload.id_objeto,
            "producto": payload.producto,
            "status": "INCOHERENTE",
            "score": None,
            "precio": payload.precio,
            "ai_mode": "contrato",
            "incoherencia_score": resultado.score_incoherencia,
        })
        return ValidacionResponse(
            id_objeto=payload.id_objeto,
            producto=payload.producto,
            score=None,
            recomendacion="Input rechazado por incoherencia detectada.",
            observaciones=resultado.observaciones,
            status="rejected",
            ai_mode="contrato",
            timestamp=datetime.utcnow().isoformat(),
        )

    # SOSPECHOSO → sandbox con precio castigado
    if resultado.estado == EstadoValidacion.SOSPECHOSO:
        logger.info(
            f"SOSPECHOSO: {payload.id_objeto} — "
            f"score={resultado.score_incoherencia} — sandbox activado"
        )
        # Continuar con IA pero marcar como sospechoso
        resultado.observaciones.append("⚠️ Sandbox: precio castigado -20%")

    # PENDIENTE → no se puede verificar
    if resultado.estado == EstadoValidacion.PENDIENTE:
        log_event({
            "type": "validation",
            "id_objeto": payload.id_objeto,
            "producto": payload.producto,
            "status": "PENDIENTE",
            "score": None,
            "precio": payload.precio,
            "ai_mode": "pending",
            "incoherencia_score": resultado.score_incoherencia,
        })
        return ValidacionResponse(
            id_objeto=payload.id_objeto,
            producto=payload.producto,
            score=None,
            recomendacion="Validación en cola. Te contactaremos en < 1 hora.",
            observaciones=resultado.observaciones,
            status="pending",
            ai_mode="pending",
            timestamp=datetime.utcnow().isoformat(),
        )

    # PASO 2: VALIDADO → scoring con IA
    logger.info(f"VALIDADO: {payload.id_objeto} — ejecutando IA ({AI_MODE})")

    try:
        if AI_MODE == "ollama":
            result = await score_with_ollama(data)
        elif AI_MODE == "gemini":
            result = await score_with_gemini(data)
        elif AI_MODE == "n8n":
            result = await score_with_n8n(data)
        else:
            result = score_mock(data)

        # Aplicar castigo de precio si es sospechoso
        if resultado.estado == EstadoValidacion.SOSPECHOSO:
            if result.get("score"):
                result["score"] = round(result["score"] * 0.8, 1)

        response = ValidacionResponse(
            id_objeto=payload.id_objeto,
            producto=payload.producto,
            score=result.get("score"),
            recomendacion=result.get("recomendacion", ""),
            observaciones=resultado.observaciones + result.get("observaciones", []),
            status="ok",
            ai_mode=AI_MODE,
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(f"Score: {response.score}/10 para {payload.producto}")

        log_event({
            "type": "validation",
            "id_objeto": payload.id_objeto,
            "producto": payload.producto,
            "status": "SOSPECHOSO" if resultado.estado == EstadoValidacion.SOSPECHOSO else "VALIDADO",
            "score": result.get("score"),
            "precio": payload.precio,
            "ai_mode": AI_MODE,
            "incoherencia_score": resultado.score_incoherencia,
        })

        return response

    except Exception as e:
        logger.error(f"Error en validación: {e}")
        result = score_mock(data)

        log_event({
            "type": "validation",
            "id_objeto": payload.id_objeto,
            "producto": payload.producto,
            "status": "VALIDADO",
            "score": result.get("score"),
            "precio": payload.precio,
            "ai_mode": f"{AI_MODE}-fallback",
            "incoherencia_score": resultado.score_incoherencia,
            "error": str(e),
        })

        return ValidacionResponse(
            id_objeto=payload.id_objeto,
            producto=payload.producto,
            score=result.get("score"),
            recomendacion=result.get("recomendacion", ""),
            observaciones=resultado.observaciones + [f"IA fallback: {e}"] + result.get("observaciones", []),
            status="ok",
            ai_mode=f"{AI_MODE}-fallback",
            timestamp=datetime.utcnow().isoformat(),
        )


# =============================================================================
# PRODUCTOS CRUD
# =============================================================================

class ProductCreate(BaseModel):
    nombre: str
    categoria: str = "food"
    precio: float
    peso_gramos: Optional[int] = None
    descripcion: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    precio: float
    peso_gramos: Optional[int] = None
    descripcion: Optional[str] = None
    creado_en: str

_products_db = []
_products_next_id = 1

@app.post("/api/products", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    global _products_next_id
    entry = {
        "id": _products_next_id,
        "nombre": product.nombre,
        "categoria": product.categoria,
        "precio": product.precio,
        "peso_gramos": product.peso_gramos,
        "descripcion": product.descripcion,
        "creado_en": datetime.utcnow().isoformat(),
    }
    _products_db.append(entry)
    _products_next_id += 1
    return entry

@app.get("/api/products", response_model=list[ProductResponse])
async def list_products(categoria: Optional[str] = None):
    if categoria:
        return [p for p in _products_db if p["categoria"] == categoria]
    return _products_db

@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    for p in _products_db:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
