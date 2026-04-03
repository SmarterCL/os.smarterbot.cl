# 🧠 SmarterOS — os.smarterbot.store

> **Ecosistema cognitivo unificado v4.3** — Core determinístico + Capa IA enchufable

---

## 📊 Estado Actual

| Capa | Estado | Descripción |
|---|---|---|
| **Core v4.2** | ✅ **Activo** | API FastAPI + Validador + N8N + Telegram + Dashboard |
| **Cognitive v4.3** | 📦 **Standby** | Bookish (retrieval) + Emdash (generación) — stubs listos |

## 🚀 Quick Start

```bash
# Core (siempre activo)
docker compose up -d

# Cognitive (cuando haya datos suficientes)
/usr/local/bin/check_cognitive_activation.sh
docker compose --profile cognitive up -d
```

## 📁 Estructura

```
os.smarterbot.cl/
├── api/                      # FastAPI — Policy Engine
│   ├── main.py              # Entry point
│   ├── routes/              # Endpoints (validar, productos)
│   ├── services/            # Validator, N8N integration
│   ├── middleware/           # Fraude, Incoherencia, Mercado
│   ├── models/              # Pydantic schemas
│   ├── utils/               # Config, logger
│   ├── cognitive_hook.py    # Hook v4.3 — fallback garantizado
│   └── requirements.txt
├── cms/                     # CMS — Content Management
│   └── content/             # Contenido dinámico
├── config/
│   └── policies.yaml        # Umbrales dinámicos
├── deploy/                  # Deployment scripts
├── scripts/                 # Utilities
├── static/                  # Frontend assets
├── services/                # v4.3 Cognitive stubs
│   ├── bookish/app.py       # Retrieval de conocimiento
│   └── emdash/app.py        # Generación de contenido
├── docker-compose.yml       # Compose con perfiles cognitivos
├── Caddyfile                # Reverse proxy
└── docs/
    └── v1-archive/          # Brain v1 docs (legacy)
```

## 🔗 Endpoints

| URL | Servicio |
|---|---|
| https://os.smarterbot.store | Portal principal |
| https://bolt.smarterbot.store | Dashboard v3.1 |
| https://docling.smarterbot.store | Parser multimodal |
| https://n8n.smarterbot.store | Automatización |
| food.smarterbot.cl | API (legacy route) |

## 🧪 Activación v4.3

Condiciones de datos:
- ✅ Total eventos ≥ 200 (actual: 50)
- ✅ Eventos reales ≥ 50 (actual: 0)
- ✅ Sandbox rate 15-45% (actual: 30%)

**Estado:** ⏳ 1/3 condiciones — esperando tráfico real

---

*"Inteligencia enchufable cuando haya datos"*
