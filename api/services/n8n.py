"""
N8N Webhook Service — Bridge to n8n workflows.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("smarter-food.n8n")


class N8NWebhookService:
    """Send data to n8n workflows for async processing."""

    def __init__(self):
        self.base_url = os.getenv("N8N_BASE_URL", "https://n8n.smarterbot.cl")
        self.timeout = int(os.getenv("N8N_TIMEOUT", "30"))

    async def send(self, workflow: str, data: dict) -> Optional[dict]:
        """Send data to an n8n webhook workflow."""
        url = f"{self.base_url}/webhook/{workflow}"
        logger.info(f"Sending to n8n: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"n8n error: {e}")
            return None

    async def trigger_food_validation(self, payload: dict) -> Optional[dict]:
        """Trigger Smarter Food validation workflow."""
        return await self.send("smarter-food", payload)
