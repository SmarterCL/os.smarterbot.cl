# Protocolo Smarter v1.0

## Principio Fundamental

**Verdad = coherencia(.env ∩ contexto ∩ input_usuario)**

Si no hay intersección → **rechazo automático** (no excepción, no log).

---

## 1. Estados de Validación

| Estado | Significado | Acción del Sistema |
|---|---|---|
| `VALIDADO` | Input coherente con realidad | Ejecuta flujo normal |
| `INCOHERENTE` | Contradicción detectada (score ≥ 2) | Bloqueo inmediato + etiqueta |
| `SOSPECHOSO` | Señales de alerta (score = 1) | Sandbox: precio castigado, revisión |
| `PENDIENTE` | No se puede verificar ahora | Cola de revisión humana |

---

## 2. Contrato de Incoherencia

Todo input pasa por este contrato **antes** de cualquier lógica de negocio.

### Verificaciones obligatorias (en orden):

1. **ENV** — ¿El nodo tiene sus axiomas configurados?
   - Sin `.env` válido → `HARD_FAIL_ENV` (no se procesa)

2. **ESTADO** — ¿El input es consistente con el estado real del sistema?
   - DB, APIs, colas, servicios disponibles
   - Ejemplo: usuario dice "500kg" pero su histórico máximo es 50kg

3. **FRAUDE** — ¿El input coincide con patrones de fraude conocidos?
   - Patrones registrados en el sistema
   - Ejemplo: misma patente, mismo teléfono, diferente nombre

4. **MERCADO** — ¿El precio está dentro del rango de mercado?
   - Referencia externa o tabla de precios
   - Ejemplo: hamburguesa a $50.000 cuando el promedio es $5.000

### Scoring:

| Verificación fallida | Puntos |
|---|---|
| Inconsistencia con estado | +1 |
| Patrón de fraude detectado | +2 |
| Precio fuera de rango (>3x) | +1 |
| Precio fuera de rango (>10x) | +2 |
| Campo obligatorio vacío | +1 |

**Umbral:**
- score = 0 → `VALIDADO`
- score = 1 → `SOSPECHOSO`
- score ≥ 2 → `INCOHERENTE`

---

## 3. Respuestas Estándar

### VALIDADO
```json
{
  "estado": "VALIDADO",
  "score": 8.5,
  "recomendacion": "...",
  "observaciones": [],
  "siguiente_paso": "ejecutar_workflow"
}
```

### SOSPECHOSO
```json
{
  "estado": "SOSPECHOSO",
  "score": 6.0,
  "recomendacion": "Producto bajo revisión. Precio ajustado -20%.",
  "observaciones": ["Precio 2.5x sobre mercado", "Sin histórico del usuario"],
  "siguiente_paso": "sandbox_precio_castigado"
}
```

### INCOHERENTE
```json
{
  "estado": "INCOHERENTE",
  "score": null,
  "recomendacion": "Input rechazado por incoherencia.",
  "observaciones": ["Patrón de fraude: misma patente, 3 usuarios distintos"],
  "siguiente_paso": "bloqueo_etiqueta_fraude"
}
```

### PENDIENTE
```json
{
  "estado": "PENDIENTE",
  "score": null,
  "recomendacion": "Validación en cola. Te contactaremos en < 1 hora.",
  "observaciones": ["Servicio de IA no disponible temporalmente"],
  "siguiente_paso": "cola_revision_humana"
}
```

---

## 4. Nodo Fractal

Cada nodo Smarter es **clonable** solo con:

```
smarter-node/
├── .env                    ← Axiomas (no negociables)
├── docker-compose.yml      ← Infraestructura
├── api/
│   ├── main.py
│   └── middleware/
│       ├── incoherencia.py ← Contrato (portable)
│       ├── fraude.py       ← Patrones conocidos
│       └── mercado.py      ← Precios de referencia
└── scripts/
    └── init.sh             ← Bootstrap automático
```

**Test de fractalidad:** ¿Puedes copiarlo a otro VPS y que funcione solo con `.env`?
Si la respuesta es no → no es fractal, es artesanal.

---

## 5. Categorías de Validación

El mismo contrato aplica a **cualquier categoría**:

| Categoría | Input típico | Verificación clave |
|---|---|---|
| `food` | Producto alimenticio | peso/precio + foto IA + ubicación |
| `vehicle` | Patente + datos | registro + histórico + score |
| `reciclaje` | Material + cantidad | histórico + capacidad logística + precio mercado |
| `servicio` | Descripción trabajo | disponibilidad + precio referencia |

---

## 6. Reglas de Oro

1. **`.env` es ley** — no config blanda, no defaults silenciosos
2. **Incoherencia bloquea** — no loguea, no alerta, no continúa
3. **Cada nodo es clonable** — sin contexto humano requerido
4. **El usuario nunca "tiene razón"** — solo pasa validación o no

---

## 7. Integración con Ecosistema

```
Input → [Contrato Incoherencia] → ¿Estado?
  ├─ VALIDADO    → n8n workflow → Odoo (factura/stock/lead)
  ├─ SOSPECHOSO  → n8n sandbox  → Odoo (precio castigado)
  ├─ INCOHERENTE → bloqueo      → Odoo (etiqueta fraude)
  └─ PENDIENTE   → cola         → Chatwoot (revisión humana)
```

---

*Smarter Fractal Framework v1.0 — "Mac para desarrollar, VPS para producir"*
