"""
Verificador de Mercado — Precios de referencia.

Tabla de precios por categoria. Se puede actualizar desde API externa.
"""
import logging
from typing import Optional

logger = logging.getLogger("smarter-food.mercado")


# Precios de referencia por categoria (CLP)
PRECIOS_MERCADO = {
    "food": {
        "hamburguesa": {"promedio": 5500, "min": 2500, "max": 12000},
        "pizza": {"promedio": 8000, "min": 4000, "max": 18000},
        "sushi": {"promedio": 10000, "min": 5000, "max": 25000},
        "ensalada": {"promedio": 4500, "min": 2000, "max": 9000},
        "default": {"promedio": 6000, "min": 1000, "max": 20000},
    },
    "vehicle": {
        "default": {"promedio": 5000000, "min": 500000, "max": 30000000},
    },
    "reciclaje": {
        "aluminio": {"promedio": 500, "min": 200, "max": 1200, "unidad": "kg"},
        "cobre": {"promedio": 4000, "min": 2000, "max": 8000, "unidad": "kg"},
        "carton": {"promedio": 50, "min": 20, "max": 120, "unidad": "kg"},
        "default": {"promedio": 100, "min": 10, "max": 500, "unidad": "kg"},
    },
}


class VerificadorMercado:
    """Verifica precios contra referencia de mercado."""

    def __init__(self, precios: dict = None):
        self._precios = precios or PRECIOS_MERCADO

    def verificar(self, categoria: str, producto: str, precio: float) -> dict:
        """
        Verifica si el precio esta dentro del rango de mercado.

        Returns:
            dict con: dentro_rango (bool), ratio, referencia, observaciones
        """
        ref = self._get_referencia(categoria, producto)

        if not ref or ref.get("promedio", 0) == 0:
            return {
                "dentro_rango": True,
                "ratio": 1.0,
                "referencia": None,
                "observaciones": ["Sin referencia de mercado para esta categoria"],
            }

        promedio = ref["promedio"]
        ratio = precio / promedio

        dentro_rango = ref.get("min", 0) <= precio <= ref.get("max", float("inf"))

        observaciones = []
        if ratio > 3:
            observaciones.append(f"Precio {ratio:.1f}x sobre referencia (${promedio})")
        elif ratio < 0.3:
            observaciones.append(f"Precio {ratio:.1f}x bajo referencia (${promedio}) — posible dumping")

        return {
            "dentro_rango": dentro_rango,
            "ratio": round(ratio, 2),
            "referencia": promedio,
            "observaciones": observaciones,
        }

    def _get_referencia(self, categoria: str, producto: str) -> Optional[dict]:
        """Busca referencia por categoria y producto."""
        cat_data = self._precios.get(categoria, {})

        # Buscar por nombre de producto
        producto_lower = producto.lower() if producto else ""
        for key, val in cat_data.items():
            if key != "default" and key in producto_lower:
                return val

        # Fallback a default de la categoria
        return cat_data.get("default")
