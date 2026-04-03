#!/usr/bin/env python3
"""
📚 BOOKISH — LATAM Price Memory Builder
Ingesta precios reales del mercado para construir base semántica.

Uso:
  1. Ejecutar como seed inicial (inyecta precios de mercado conocidos)
  2. Llamar POST /ingest con cada evento real validado
  3. Bookish construye clusters de precio por producto
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

# ── PRECIOS DE MERCADO LATAM (seed data) ──────────────
# Fuente: observación real del mercado chileno
# Esto es lo que Bookish usa como "memoria base" antes de aprender

MERCADO_CHILE = {
    # Alimentos
    "hamburguesa clasica":    {"low": 5500,  "avg": 8500,  "high": 12000},
    "hamburguesa doble":      {"low": 7500,  "avg": 11000, "high": 15000},
    "hamburguesa completa":   {"low": 7000,  "avg": 10000, "high": 14000},
    "pizza margarita":        {"low": 7000,  "avg": 11000, "high": 16000},
    "pizza pepperoni":        {"low": 8000,  "avg": 12000, "high": 18000},
    "pizza familiar":         {"low": 10000, "avg": 15000, "high": 22000},
    "ensalada cesar":         {"low": 4500,  "avg": 7000,  "high": 10000},
    "ensalada mixta":         {"low": 3500,  "avg": 5500,  "high": 8000},
    "cafe americano":         {"low": 1000,  "avg": 2000,  "high": 3500},
    "capuchino":              {"low": 1500,  "avg": 2500,  "high": 4000},
    "coca cola 2l":           {"low": 1800,  "avg": 2500,  "high": 3500},
    "coca cola lata":         {"low": 800,   "avg": 1200,  "high": 1800},
    "jugo natural":           {"low": 2000,  "avg": 3500,  "high": 5000},
    "sushi roll":             {"low": 7000,  "avg": 12000, "high": 18000},
    "sushi 20 piezas":        {"low": 12000, "avg": 18000, "high": 25000},
    "tacos x3":               {"low": 3000,  "avg": 5500,  "high": 8000},
    "tacos x5":               {"low": 5000,  "avg": 8000,  "high": 12000},
    "helado artesanal":       {"low": 2000,  "avg": 3500,  "high": 5000},
    "completo italiano":      {"low": 1500,  "avg": 2500,  "high": 3500},
    "sandwich":               {"low": 2000,  "avg": 3500,  "high": 5500},
    "empanada":               {"low": 1200,  "avg": 2000,  "high": 3000},
    "pastel choclo":          {"low": 3000,  "avg": 5000,  "high": 7500},
    "porcion pollo":          {"low": 3500,  "avg": 6000,  "high": 9000},
    "costillar":              {"low": 6000,  "avg": 10000, "high": 15000},
    "ceviche":                {"low": 6000,  "avg": 10000, "high": 15000},
    "carbonada":              {"low": 3000,  "avg": 5000,  "high": 7000},
    "caldo tlalpeno":         {"low": 3000,  "avg": 5000,  "high": 7000},
    "fish and chips":         {"low": 6000,  "avg": 9000,  "high": 13000},
    "milanesa":               {"low": 4000,  "avg": 7000,  "high": 10000},
    "bistec a lo pobre":      {"low": 5000,  "avg": 8000,  "high": 12000},
    "choripan":               {"low": 1000,  "avg": 2000,  "high": 3000},
    "anticucho":              {"low": 1000,  "avg": 2000,  "high": 3000},
    # Bebidas
    "cerveza artesanal":      {"low": 2500,  "avg": 4500,  "high": 7000},
    "cerveza lata":           {"low": 800,   "avg": 1500,  "high": 2200},
    "copa vino":              {"low": 2000,  "avg": 3500,  "high": 6000},
    "botella vino":           {"low": 4000,  "avg": 8000,  "high": 15000},
    "pisco sour":             {"low": 3000,  "avg": 5000,  "high": 7500},
    "terremoto":              {"low": 2500,  "avg": 4000,  "high": 6000},
    "agua mineral":           {"low": 500,   "avg": 1200,  "high": 2000},
    # Tech
    "laptop gamer":           {"low": 350000, "avg": 650000, "high": 1200000},
    "laptop basica":          {"low": 200000, "avg": 350000, "high": 550000},
    "iphone 15":              {"low": 750000, "avg": 1000000, "high": 1400000},
    "iphone 14":              {"low": 550000, "avg": 800000, "high": 1100000},
    "airpods pro":            {"low": 130000, "avg": 200000, "high": 280000},
    "airpods":                {"low": 80000,  "avg": 130000, "high": 180000},
    "samsung galaxy s24":     {"low": 500000, "avg": 750000, "high": 1000000},
    "xiaomi redmi":           {"low": 80000,  "avg": 150000, "high": 250000},
    # Ropa
    "zapatillas nike":        {"low": 40000,  "avg": 70000,  "high": 120000},
    "zapatillas adidas":      {"low": 40000,  "avg": 70000,  "high": 120000},
    "polera basica":          {"low": 5000,   "avg": 12000,  "high": 20000},
    "jeans":                  {"low": 15000,  "avg": 30000,  "high": 55000},
    "camisa":                 {"low": 10000,  "avg": 20000,  "high": 35000},
    "chaqueta":               {"low": 20000,  "avg": 45000,  "high": 80000},
}


def normalize_product_name(name: str) -> str:
    """Normaliza nombre de producto para matching."""
    return name.lower().strip()


def get_price_range(product: str) -> Optional[dict]:
    """Obtiene rango de precio para un producto conocido."""
    normalized = normalize_product_name(product)

    # Exact match
    if normalized in MERCADO_CHILE:
        return MERCADO_CHILE[normalized]

    # Fuzzy match (contains)
    for key, val in MERCADO_CHILE.items():
        if key in normalized or normalized in key:
            return val

    # Category-based fallback
    if any(w in normalized for w in ["pizza"]):
        return {"low": 7000, "avg": 12000, "high": 18000}
    if any(w in normalized for w in ["burger", "hamburguesa"]):
        return {"low": 5500, "avg": 9000, "high": 14000}
    if any(w in normalized for w in ["cafe", "coffee"]):
        return {"low": 1000, "avg": 2200, "high": 3500}
    if any(w in normalized for w in ["laptop", "notebook", "portatil"]):
        return {"low": 200000, "avg": 500000, "high": 900000}
    if any(w in normalized for w in ["phone", "celular", "telefono", "iphone", "samsung"]):
        return {"low": 80000, "avg": 600000, "high": 1200000}

    return None


def score_price_coherence(product: str, price: float) -> dict:
    """
    Evalúa coherencia de precio contra memoria de mercado.

    Returns:
        {
            "known": bool,
            "range": {"low": X, "avg": Y, "high": Z},
            "deviation_pct": float,
            "status": "VALID" | "SANDBOX" | "REJECTED",
            "confidence": float 0-1
        }
    """
    price_range = get_price_range(product)

    if not price_range:
        return {
            "known": False,
            "range": None,
            "deviation_pct": None,
            "status": "SANDBOX",  # desconocido → sandbox por defecto
            "confidence": 0.2,
        }

    avg = price_range["avg"]
    low = price_range["low"]
    high = price_range["high"]

    if avg == 0:
        deviation_pct = 0
    else:
        deviation_pct = abs(price - avg) / avg * 100

    if low <= price <= high:
        status = "VALID"
        confidence = 1.0 - (deviation_pct / 100 * 0.5)
    elif price < low * 0.5 or price > high * 3:
        status = "REJECTED"
        confidence = 0.9
    else:
        status = "SANDBOX"
        confidence = 0.5

    return {
        "known": True,
        "range": price_range,
        "deviation_pct": round(deviation_pct, 1),
        "status": status,
        "confidence": round(confidence, 2),
    }


def ingest_event(product: str, price: float, user_id: str = "",
                 status: str = "") -> dict:
    """
    Ingesta un evento de precio para construir memoria adaptativa.
    """
    coherence = score_price_coherence(product, price)

    record = {
        "producto": normalize_product_name(product),
        "precio": price,
        "user_id": user_id,
        "status": status or coherence["status"],
        "coherence": coherence,
        "ts": int(time.time()),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Append to learning log
    learning_log = Path("/var/log/smarter/bookish_learning.log")
    learning_log.parent.mkdir(parents=True, exist_ok=True)
    with open(learning_log, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record


def get_market_summary() -> dict:
    """Resumen de memoria de mercado."""
    return {
        "total_products": len(MERCADO_CHILE),
        "categories": {
            "food": sum(1 for p in MERCADO_CHILE if any(w in p for w in [
                "hamburguesa", "pizza", "ensalada", "sushi", "tacos",
                "helado", "completo", "empanada", "pastel", "pollo",
                "costillar", "ceviche", "milanesa", "bistec", "choripan",
                "anticucho", "sandwich", "cafe", "capuchino"
            ])),
            "drink": sum(1 for p in MERCADO_CHILE if any(w in p for w in [
                "coca cola", "jugo", "cerveza", "vino", "pisco",
                "terremoto", "agua"
            ])),
            "tech": sum(1 for p in MERCADO_CHILE if any(w in p for w in [
                "laptop", "iphone", "airpods", "samsung", "xiaomi"
            ])),
            "clothing": sum(1 for p in MERCADO_CHILE if any(w in p for w in [
                "zapatillas", "polera", "jeans", "camisa", "chaqueta"
            ])),
        },
    }


# ── Flask app (when running as service) ───────────────
if __name__ == "__main__":
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "bookish",
            "version": "4.3.0",
            "mode": "price-memory",
            "products": len(MERCADO_CHILE),
        })

    @app.route("/price-range", methods=["GET"])
    def price_range():
        product = request.args.get("product", "")
        result = get_price_range(product)
        if result:
            return jsonify({"product": product, "range": result})
        return jsonify({"product": product, "error": "not found"}), 404

    @app.route("/score", methods=["POST"])
    def score():
        data = request.json
        result = score_price_coherence(
            data.get("producto", ""),
            data.get("precio", 0)
        )
        return jsonify(result)

    @app.route("/ingest", methods=["POST"])
    def ingest():
        data = request.json
        result = ingest_event(
            data.get("producto", ""),
            data.get("precio", 0),
            data.get("user_id", ""),
            data.get("status", ""),
        )
        return jsonify(result)

    @app.route("/summary")
    def summary():
        return jsonify(get_market_summary())

    port = int(os.getenv("BOOKISH_PORT", 8004))
    print(f"📚 Bookish LATAM Price Memory running on port {port}")
    print(f"   Products in memory: {len(MERCADO_CHILE)}")
    app.run(host="0.0.0.0", port=port)
