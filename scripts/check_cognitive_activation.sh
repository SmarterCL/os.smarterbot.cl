#!/bin/bash
# Verifica si las condiciones para activar la capa cognitiva v4.3 se cumplen

DB_PATH="/var/lib/smarter/metrics.db"

echo "🧠 Verificando condiciones para activar capa cognitiva v4.3..."
echo "───────────────────────────────────────────────────────────"

# Check total events
total=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events;" 2>/dev/null || echo "0")
echo "📊 Total eventos: $total"

# Check real events (from API, not injected)
real=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM events WHERE user_id != 'test' AND user_id != 'gemini';" 2>/dev/null || echo "0")
echo "📊 Eventos reales: $real"

# Check sandbox rate stability
sandbox_rate=$(sqlite3 $DB_PATH "SELECT ROUND(COUNT(CASE WHEN status='SANDBOX' THEN 1 END)*100.0/COUNT(*), 1) FROM events;" 2>/dev/null || echo "0")
echo "📊 Sandbox rate: ${sandbox_rate}%"

# Check conditions
echo ""
echo "───────────────────────────────────────────────────────────"
echo "Condiciones de activación:"

conditions_met=0

if [ "$total" -ge 200 ]; then
  echo "  ✅ Total eventos ≥ 200 ($total)"
  ((conditions_met++))
else
  echo "  ❌ Total eventos ≥ 200 ($total)"
fi

if [ "$real" -ge 50 ]; then
  echo "  ✅ Eventos reales ≥ 50 ($real)"
  ((conditions_met++))
else
  echo "  ❌ Eventos reales ≥ 50 ($real)"
fi

# Check sandbox rate stability (between 15-45%)
sandbox_int=${sandbox_rate%.*}
if [ "$sandbox_int" -ge 15 ] && [ "$sandbox_int" -le 45 ]; then
  echo "  ✅ Sandbox rate estable (15-45%) (${sandbox_rate}%)"
  ((conditions_met++))
else
  echo "  ❌ Sandbox rate estable (15-45%) (${sandbox_rate}%)"
fi

echo ""
echo "───────────────────────────────────────────────────────────"
echo "Condiciones cumplidas: $conditions_met/3"

if [ "$conditions_met" -eq 3 ]; then
  echo ""
  echo "🚀 LISTO PARA ACTIVAR CAPA COGNITIVA"
  echo "Ejecutar: docker compose --profile cognitive up -d"
else
  echo ""
  echo "⏳ AÚN NO LISTO - Seguir capturando eventos"
fi
