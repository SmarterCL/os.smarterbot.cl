#!/bin/bash
# Quick DNS Validation Script for SmarterOS Brain
# Run this after updating DNS records to verify propagation

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     SmarterOS Brain - DNS Validation Script v1.0          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

TARGET_IP="89.116.23.167"
DOMAINS=(
  "smarterbot.cl"
  "www.smarterbot.cl"
  "api.smarterbot.cl"
  "ledger.smarterbot.cl"
  "biostack.smarterbot.cl"
  "monitoring.smarterbot.cl"
  "graph.smarterbot.cl"
)

echo "🔍 Checking DNS propagation to $TARGET_IP..."
echo ""

all_good=true

for domain in "${DOMAINS[@]}"; do
  echo -n "Checking $domain ... "
  
  # Try to resolve with dig
  result=$(dig +short "$domain" @8.8.8.8 2>/dev/null || echo "FAIL")
  
  if [ "$result" = "$TARGET_IP" ]; then
    echo "✅ OK ($result)"
  else
    echo "⚠️  PENDING (got: $result)"
    all_good=false
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test HTTPS endpoints
echo "🔐 Testing HTTPS endpoints..."
echo ""

ENDPOINTS=(
  "https://smarterbot.cl/health"
  "https://api.smarterbot.cl/health"
  "https://ledger.smarterbot.cl/health"
  "https://biostack.smarterbot.cl/health"
)

for endpoint in "${ENDPOINTS[@]}"; do
  echo -n "Testing $endpoint ... "
  
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -k "$endpoint" 2>/dev/null || echo "000")
  
  if [ "$status" = "200" ]; then
    echo "✅ OK (HTTP $status)"
  elif [ "$status" = "000" ]; then
    echo "⏳ PENDING (no response yet)"
  else
    echo "⚠️  Got HTTP $status"
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$all_good" = true ]; then
  echo "✅ All DNS records propagated correctly!"
  echo ""
  echo "Next steps:"
  echo "  1. Access https://smarterbot.cl in your browser"
  echo "  2. Verify SSL certificate is valid (green lock)"
  echo "  3. Test API: curl https://api.smarterbot.cl/health"
  echo "  4. View dashboard: https://monitoring.smarterbot.cl"
else
  echo "⏳ Some DNS records still propagating..."
  echo ""
  echo "Typical propagation time: 5-30 minutes"
  echo "Run this script again in 5-10 minutes"
  echo ""
  echo "For immediate check with your local ISP:"
  echo "  nslookup smarterbot.cl"
  echo "  dig smarterbot.cl +short"
end

echo ""
