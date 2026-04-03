"""
Contrato de Incoherencia — Middleware obligatorio.

Todo input pasa por aqui ANTES de cualquier logica de negocio.
Regla: incoherencia BLOQUEA, no loguea.
"""
import os
import logging
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("smarter-food.incoherencia")

POLICIES_PATH = Path("/var/www/smarter_latam/config/policies.yaml")


class EstadoValidacion(str, Enum):
    VALIDADO = "VALIDADO"
    SOSPECHOSO = "SOSPECHOSO"
    INCOHERENTE = "INCOHERENTE"
    PENDIENTE = "PENDIENTE"


@dataclass
class ResultadoContrato:
    estado: EstadoValidacion
    score_incoherencia: int = 0
    score_calidad: Optional[float] = None
    observaciones: list = field(default_factory=list)
    siguiente_paso: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ContratoIncoherencia:
    """
    Verifica coherencia entre: .env ∩ contexto ∩ input_usuario

    Scoring:
      0 → VALIDADO
      1 → SOSPECHOSO
      ≥2 → INCOHERENTE
    """

    def __init__(self):
        self._umbrales = self._load_policies()

    def _load_policies(self) -> dict:
        """Load thresholds from policies.yaml, fallback to defaults."""
        defaults = {
            "sospechoso": 1,
            "incoherente": 2,
            "precio_mult_warn": 3.0,
            "precio_mult_reject": 10.0,
        }
        try:
            import yaml
            if POLICIES_PATH.exists():
                with open(POLICIES_PATH) as f:
                    cfg = yaml.safe_load(f)
                precio = cfg.get("precio", {})
                defaults["precio_mult_warn"] = float(precio.get("warn_mult", 3.0))
                defaults["precio_mult_reject"] = float(precio.get("reject_mult", 10.0))
                sandbox = cfg.get("sandbox", {})
                defaults["sandbox_penalty"] = float(sandbox.get("penalty", 0.8))
        except Exception:
            pass  # Use defaults if yaml unavailable
        return defaults

    def evaluar(self, input_data: dict, contexto: dict, env_ok: bool) -> ResultadoContrato:
        """
        Evalua el contrato de incoherencia.

        Args:
            input_data: Datos del usuario (request body)
            contexto: Estado real del sistema (DB, historicos, etc.)
            env_ok: Si el .env del nodo esta configurado

        Returns:
            ResultadoContrato con estado y observaciones
        """
        score = 0
        observaciones = []

        # 1. ENV — axiomas del nodo
        if not env_ok:
            return ResultadoContrato(
                estado=EstadoValidacion.PENDIENTE,
                score_incoherencia=99,
                observaciones=["Nodo sin configuracion valida (.env)"],
                siguiente_paso="configurar_env",
            )

        # 2. Campos obligatorios
        campos_requeridos = ["id_objeto", "producto"]
        for campo in campos_requeridos:
            if not input_data.get(campo):
                score += 1
                observaciones.append(f"Campo obligatorio vacio: {campo}")

        # 3. Consistencia con estado real
        estado_score = self._verificar_estado(input_data, contexto)
        score += estado_score["puntos"]
        observaciones.extend(estado_score["observaciones"])

        # 4. Patron de fraude
        fraude_score = self._verificar_fraude(input_data, contexto)
        score += fraude_score["puntos"]
        observaciones.extend(fraude_score["observaciones"])

        # 5. Precio vs mercado
        precio_score = self._verificar_precio(input_data, contexto)
        score += precio_score["puntos"]
        observaciones.extend(precio_score["observaciones"])

        # Determinar estado
        estado, siguiente = self._determinar_estado(score, input_data)

        return ResultadoContrato(
            estado=estado,
            score_incoherencia=score,
            observaciones=observaciones,
            siguiente_paso=siguiente,
        )

    def _verificar_estado(self, input_data: dict, contexto: dict) -> dict:
        """Verifica consistencia con el estado real del sistema."""
        puntos = 0
        observaciones = []

        # Verificar si el usuario tiene historico
        usuario_id = input_data.get("usuario_id", "")
        historico = contexto.get("usuarios", {}).get(usuario_id, {})

        if usuario_id and not historico:
            puntos += 1
            observaciones.append("Sin historico del usuario")

        # Verificar coherencia de cantidad vs historico
        if historico and "cantidad_maxima" in historico:
            cantidad = input_data.get("peso_gramos") or input_data.get("cantidad", 0)
            if cantidad and cantidad > historico["cantidad_maxima"] * 5:
                puntos += 1
                observaciones.append(
                    f"Cantidad {cantidad} excede 5x el maximo historico "
                    f"({historico['cantidad_maxima']})"
                )

        return {"puntos": puntos, "observaciones": observaciones}

    def _verificar_fraude(self, input_data: dict, contexto: dict) -> dict:
        """Detecta patrones de fraude conocidos."""
        puntos = 0
        observaciones = []

        patrones = contexto.get("patrones_fraude", [])
        id_objeto = input_data.get("id_objeto", "")

        for patron in patrones:
            if patron.get("id_objeto") == id_objeto:
                puntos += 2
                observaciones.append(f"Patrón de fraude detectado: {patron.get('tipo', 'desconocido')}")
                break

        # Verificar reuso de identidad
        usuarios_mismo_objeto = contexto.get("objetos_usuarios", {}).get(id_objeto, [])
        if len(usuarios_mismo_objeto) > 1:
            puntos += 2
            observaciones.append(
                f"ID objeto {id_objeto} usado por {len(usuarios_mismo_objeto)} usuarios distintos"
            )

        return {"puntos": puntos, "observaciones": observaciones}

    def _verificar_precio(self, input_data: dict, contexto: dict) -> dict:
        """Verifica precio vs referencia de mercado."""
        puntos = 0
        observaciones = []

        precio = input_data.get("precio")
        categoria = input_data.get("categoria", "food")
        producto = input_data.get("producto", "")

        if not precio:
            return {"puntos": 0, "observaciones": []}

        # Buscar referencia en la estructura anidada de precios
        precios_mercado = contexto.get("precios_mercado", {})
        cat_data = precios_mercado.get(categoria, {})

        # Buscar por subcategoria (producto) o usar default
        referencia = None
        producto_lower = producto.lower() if producto else ""
        for key, val in cat_data.items():
            if key != "default" and key in producto_lower:
                referencia = val.get("promedio")
                break
        if not referencia:
            referencia = cat_data.get("default", {}).get("promedio")

        if referencia and referencia > 0:
            ratio = precio / referencia

            if ratio >= self._umbrales["precio_mult_reject"]:
                puntos += 2
                observaciones.append(
                    f"Precio ${precio:.0f} es {ratio:.0f}x sobre mercado (${referencia:.0f})"
                )
            elif ratio >= self._umbrales["precio_mult_warn"]:
                puntos += 1
                observaciones.append(
                    f"Precio ${precio:.0f} es {ratio:.1f}x sobre mercado (${referencia:.0f})"
                )

        return {"puntos": puntos, "observaciones": observaciones}

    def _determinar_estado(self, score: int, input_data: dict) -> tuple:
        """Determina el estado final basado en el score."""
        if score == 0:
            return EstadoValidacion.VALIDADO, "ejecutar_workflow"
        elif score == 1:
            return EstadoValidacion.SOSPECHOSO, "sandbox_precio_castigado"
        else:
            return EstadoValidacion.INCOHERENTE, "bloqueo_etiqueta_fraude"
