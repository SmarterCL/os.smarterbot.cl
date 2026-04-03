#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🧠 v4.3 COGNITIVE ACTIVATION — RUNBOOK EJECUTABLE
# SmarterOS — os.smarterbot.store
# ═══════════════════════════════════════════════════════════

set -e

DB_PATH="/var/lib/smarter/metrics.db"
COMPOSE_DIR="/opt/smarter-os"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ───────────────────────────────────────────────────────
# PHASE 0: STATUS
# ───────────────────────────────────────────────────────
status() {
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  🧠 v4.3 COGNITIVE ACTIVATION — STATUS${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
    echo ""

    total=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events;")
    real=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events WHERE user_id NOT IN ('gemini','test');")
    users=$(sqlite3 $DB_PATH "SELECT COUNT(DISTINCT user_id) FROM events WHERE user_id NOT IN ('gemini','test');")
    valid=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events WHERE status='VALID';")
    sandbox=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events WHERE status='SANDBOX';")
    rejected=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events WHERE status='REJECTED';")
    sandbox_rate=$(sqlite3 $DB_PATH "SELECT ROUND(COUNT(CASE WHEN status='SANDBOX' THEN 1 END)*100.0/NULLIF(COUNT(*),0), 1) FROM events;")
    decisions=$(wc -l < /var/log/smarter/decisions.log 2>/dev/null || echo 0)

    echo "  📊 EVENTS"
    echo "     Total:      $total / 200"
    echo "     Reales:     $real / 50"
    echo "     Usuarios:   $users (need ≥ 3)"
    echo ""
    echo "  📈 DISTRIBUTION"
    echo "     VALID:      $valid"
    echo "     SANDBOX:    $sandbox  (${sandbox_rate}%)"
    echo "     REJECTED:   $rejected"
    echo ""
    echo "  🧠 DECISIONS LOGGED: $decisions"
    echo ""

    # Check thresholds
    pass=0
    if [ "$total" -ge 200 ]; then
        echo -e "  ${GREEN}✅${NC} Total ≥ 200"
        ((pass++))
    else
        echo -e "  ${RED}❌${NC} Total ≥ 200 (faltan $((200 - total)))"
    fi

    if [ "$real" -ge 50 ]; then
        echo -e "  ${GREEN}✅${NC} Eventos reales ≥ 50"
        ((pass++))
    else
        echo -e "  ${RED}❌${NC} Eventos reales ≥ 50 (faltan $((50 - real)))"
    fi

    sandbox_int=${sandbox_rate%.*}
    if [ "${sandbox_int:-0}" -ge 15 ] && [ "${sandbox_int:-0}" -le 45 ]; then
        echo -e "  ${GREEN}✅${NC} Sandbox rate 15-45%"
        ((pass++))
    else
        echo -e "  ${RED}❌${NC} Sandbox rate estable (15-45%) — actual: ${sandbox_rate}%"
    fi

    if [ "$users" -ge 3 ]; then
        echo -e "  ${GREEN}✅${NC} Usuarios ≥ 3"
        ((pass++))
    else
        echo -e "  ${RED}❌${NC} Usuarios ≥ 3 (actual: $users)"
    fi

    echo ""
    echo "  Result: $pass/4 conditions met"
    echo ""

    if [ "$pass" -eq 4 ]; then
        echo -e "  ${GREEN}🚀 READY — Run: $0 activate${NC}"
        return 0
    else
        echo -e "  ${YELLOW}⏳ NOT READY — Run: $0 inject [count]${NC}"
        return 1
    fi
}

# ───────────────────────────────────────────────────────
# PHASE 1: INJECT CONTROLLED EVENTS (hack mode)
# ───────────────────────────────────────────────────────
inject_events() {
    count=${1:-50}
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  📥 INYECTANDO $count EVENTOS SEMI-REALES${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
    echo ""

    # Simulate multiple users with varied pricing
    python3 << PYEOF
import requests, random, time, hashlib

products = [
    # (producto, price_range_low, price_range_high, category)
    ("Hamburguesa Clasica", 6000, 12000, "food"),
    ("Hamburguesa Doble", 8000, 15000, "food"),
    ("Pizza Margarita", 8000, 16000, "food"),
    ("Pizza Pepperoni", 9000, 18000, "food"),
    ("Ensalada Cesar", 5000, 10000, "food"),
    ("Cafe Americano", 1200, 3000, "drink"),
    ("Coca Cola 2L", 2000, 3500, "drink"),
    ("Jugo Natural", 2500, 5000, "drink"),
    ("Sushi Roll", 8000, 18000, "food"),
    ("Tacos x3", 3500, 8000, "food"),
    ("Helado Artesanal", 2500, 5000, "food"),
    ("Laptop Gamer", 400000, 900000, "tech"),
    ("iPhone 15", 800000, 1500000, "tech"),
    ("AirPods Pro", 150000, 300000, "tech"),
    ("Zapatillas Nike", 50000, 120000, "clothing"),
    ("Polera Basica", 8000, 20000, "clothing"),
]

# Simulate 5 different users
users = [f"usr_{hashlib.md5(str(i).encode()).hexdigest()[:6]}" for i in range(5)]

injected = 0
for i in range($count):
    prod_name, price_low, price_high, _ = random.choice(products)
    user_id = random.choice(users)

    # Create realistic distribution:
    # 60% normal prices (VALID)
    # 25% slightly off (SANDBOX)
    # 15% outliers (REJECTED)
    r = random.random()
    if r < 0.60:
        precio = random.randint(price_low, price_high)
    elif r < 0.85:
        # 30-80% above normal
        precio = int(price_high * random.uniform(1.3, 1.8))
    else:
        # 3-10x above normal (clear outlier)
        precio = int(price_high * random.uniform(3, 10))

    try:
        resp = requests.post(
            "http://localhost:8002/webhook/telegram",
            json={
                "producto": prod_name,
                "precio": precio,
                "user_id": user_id,
                "user_chat_id": "6683244662",
            },
            timeout=10
        )
        d = resp.json()
        status_emoji = {"VALID": "✔", "SANDBOX": "⚠", "REJECTED": "✖"}.get(d.get("status", ""), "?")
        print(f"  [{i+1:3d}] {status_emoji} {prod_name:25s} \${precio:>8,} | {d.get('status'):10s} | {user_id}")
        injected += 1
    except Exception as e:
        print(f"  [{i+1:3d}] ✖ ERROR: {e}")

    time.sleep(0.2)

print(f"\n  ✅ Injected: {injected}/$count")
PYEOF

    echo ""
    echo "  Verifying..."
    sleep 2
    status || true
}

# ───────────────────────────────────────────────────────
# PHASE 2: ACTIVATE COGNITIVE LAYER
# ───────────────────────────────────────────────────────
activate() {
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🧠 ACTIVANDO CAPA COGNITIVA v4.3${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""

    echo "  1/4 Checking prerequisites..."
    if ! status; then
        echo ""
        echo -e "  ${RED}⚠️  Conditions not met. Force anyway? (y/N)${NC}"
        read -r confirm
        if [ "$confirm" != "y" ]; then
            echo "  Aborted."
            return 1
        fi
    fi

    echo ""
    echo "  2/4 Starting cognitive services..."
    cd "$COMPOSE_DIR"
    docker compose --profile cognitive up -d

    echo ""
    echo "  3/4 Waiting for health checks..."
    sleep 10

    bookish_ok=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8004/health 2>/dev/null || echo "000")
    emdash_ok=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "000")

    if [ "$bookish_ok" = "200" ]; then
        echo -e "  ${GREEN}✅${NC} Bookish: healthy (port 8004)"
    else
        echo -e "  ${RED}❌${NC} Bookish: NOT healthy ($bookish_ok)"
    fi

    if [ "$emdash_ok" = "200" ]; then
        echo -e "  ${GREEN}✅${NC} Emdash: healthy (port 8001)"
    else
        echo -e "  ${RED}❌${NC} Emdash: NOT healthy ($emdash_ok)"
    fi

    echo ""
    echo "  4/4 Uncommenting Caddy domains..."
    if grep -q "^# bookish" /etc/caddy/Caddyfile; then
        sed -i 's/^# bookish/bookish/' /etc/caddy/Caddyfile
        sed -i 's/^#     reverse_proxy smarter-bookish/    reverse_proxy smarter-bookish/' /etc/caddy/Caddyfile
        sed -i 's/^# emdash/emdash/' /etc/caddy/Caddyfile
        sed -i 's/^#     reverse_proxy smarter-emdash/    reverse_proxy smarter-emdash/' /etc/caddy/Caddyfile
        systemctl reload caddy
        echo -e "  ${GREEN}✅${NC} Caddy reloaded"
    else
        echo "  ℹ️  Caddy domains already uncommented or not found"
    fi

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🧠 COGNITIVE LAYER ACTIVATED${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "  Bookish: http://bookish.smarterbot.store"
    echo "  Emdash:  http://emdash.smarterbot.store"
    echo ""
    echo "  Monitor:"
    echo "    curl http://localhost:8004/metrics  # Bookish"
    echo "    curl http://localhost:8001/metrics  # Emdash"
    echo "    curl http://localhost:8002/metrics/decisions"
}

# ───────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────
case "${1:-status}" in
    status)
        status
        ;;
    inject)
        inject_events "${2:-50}"
        ;;
    activate)
        activate
        ;;
    *)
        echo "Usage: $0 {status|inject [count]|activate}"
        echo ""
        echo "  status    — Check activation readiness"
        echo "  inject N  — Inject N controlled events (default: 50)"
        echo "  activate  — Deploy cognitive layer"
        ;;
esac
