"""
Validator Service — Universal scoring engine.
Mirrors EcoCupon pattern: ID + data → score via AI.
Supports Gemini AI and n8n webhook backends.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger("smarter-food.validator")


class ValidatorService:
    """Universal validator — food, vehicles, anything."""

    def __init__(self):
        self.n8n_webhook_url = os.getenv(
            "N8N_VALIDATOR_WEBHOOK",
            "https://n8n.smarterbot.cl/webhook/smarter-food"
        )
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.timeout = int(os.getenv("VALIDATOR_TIMEOUT", "30"))

    async def validate(self, payload: dict) -> dict:
        """Validate a product/object. Tries n8n webhook first, falls back to local."""
        logger.info(f"Validating: {payload.get('id_objeto')} — {payload.get('producto')}")

        try:
            result = await self._call_n8n_webhook(payload)
            if result and result.get("score") is not None:
                logger.info(f"n8n validation complete: score={result['score']}")
                return result
        except Exception as e:
            logger.warning(f"n8n webhook failed: {e}, falling back to local")

        return self._local_pending_response(payload)

    async def _call_n8n_webhook(self, payload: dict) -> Optional[dict]:
        """Send to n8n for AI processing."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.n8n_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    def _local_pending_response(self, payload: dict) -> dict:
        """Return pending response when AI backend is unavailable."""
        return {
            "id_objeto": payload.get("id_objeto", ""),
            "producto": payload.get("producto", ""),
            "score": None,
            "recomendacion": "Recibimos tu producto. Te contactaremos en menos de 1 hora.",
            "observaciones": ["Validación pendiente — IA procesando"],
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def validate_image(self, image_url: str, producto: str) -> dict:
        """Validate product quality via image analysis (Gemini Vision)."""
        if not self.gemini_api_key:
            return {"error": "GEMINI_API_KEY not configured"}

        prompt = (
            f"Analiza la calidad de este producto: {producto}. "
            "Evalúa: apariencia, frescura, presentación. "
            "Devuelve JSON con: score (0-10), recomendacion (string), "
            "observaciones (array de strings)."
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                params={"key": self.gemini_api_key},
                json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_url}}
                        ]
                    }]
                }
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
