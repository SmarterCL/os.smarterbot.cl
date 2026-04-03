"""
Detector de Fraude — Patrones conocidos.

Cada patron es una regla portable que funciona en cualquier nodo.
"""
import logging
from typing import Optional

logger = logging.getLogger("smarter-food.fraude")


class DetectorFraude:
    """Detecta patrones de fraude en inputs."""

    def __init__(self):
        self._patrones = []

    def registrar_patron(self, tipo: str, regla: dict, severidad: int = 2):
        """
        Registra un patron de fraude.

        Args:
            tipo: Categoria del patron (ej: "identidad_reusada")
            regla: Diccionario con la regla
            severidad: Puntos que suma (default 2)
        """
        self._patrones.append({
            "tipo": tipo,
            "regla": regla,
            "severidad": severidad,
        })

    def evaluar(self, input_data: dict, contexto: dict) -> list:
        """
        Evalua input contra todos los patrones.

        Returns:
            Lista de patrones detectados
        """
        detectados = []

        for patron in self._patrones:
            if self._match(patron["regla"], input_data, contexto):
                detectados.append(patron)
                logger.warning(
                    f"Fraude detectado: {patron['tipo']} "
                    f"(severidad={patron['severidad']})"
                )

        return detectados

    def _match(self, regla: dict, input_data: dict, contexto: dict) -> bool:
        """Evalua si una regla matchea con el input."""
        regla_tipo = regla.get("tipo", "")

        if regla_tipo == "identidad_reusada":
            id_objeto = input_data.get("id_objeto", "")
            usuarios = contexto.get("objetos_usuarios", {}).get(id_objeto, [])
            return len(usuarios) > 1

        elif regla_tipo == "cantidad_anomala":
            cantidad = input_data.get("peso_gramos") or input_data.get("cantidad", 0)
            maximo = regla.get("maximo", float("inf"))
            return cantidad > maximo

        elif regla_tipo == "precio_fuera_rango":
            precio = input_data.get("precio", 0)
            min_precio = regla.get("min_precio", 0)
            max_precio = regla.get("max_precio", float("inf"))
            return precio < min_precio or precio > max_precio

        return False
