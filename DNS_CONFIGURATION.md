# DNS Configuration Guide - SmarterOS Brain v1.0

## Current DNS State (❌ BROKEN)

```
smarterbot.cl (root @)       → 216.198.79.1      [OLD IP - pointing to old infrastructure]
www.smarterbot.cl            → 81c926cb1110b381.vercel-dns-017.com → 216.198.79.1  [Vercel redirect]
api.smarterbot.cl            → 89.116.23.167     [CORRECT]
```

**Problem**: Main domain is pointing to OLD infrastructure. When clients visit `smarterbot.cl`, they hit dead server.

---

## Required DNS Changes (✅ FIX)

**New target IP**: `89.116.23.167` (Hostinger VPS)

| Record Type | Subdomain | Current Value | New Value | TTL | Purpose |
|-------------|-----------|---------------|-----------|-----|---------|
| A | @ (root) | 216.198.79.1 | **89.116.23.167** | 3600 | Main domain → Orchestrator (Caddy) |
| A | www | Vercel alias | **89.116.23.167** | 3600 | www redirect → Orchestrator (Caddy) |
| A | api | 89.116.23.167 | **89.116.23.167** | 3600 | API → RoutingBrain (fee optimization) |
| A | ledger | (new) | 89.116.23.167 | 3600 | Ledger → LedgerBrain (accounting) |
| A | biostack | (new) | 89.116.23.167 | 3600 | Market analysis → BioStack |
| A | monitoring | (new) | 89.116.23.167 | 3600 | Monitoring → Grafana |
| A | graph | (new) | 89.116.23.167 | 3600 | Graph DB → Neo4j Browser |

---

## Step-by-Step: Update DNS at Registrar

### Where to make changes:
- **Domain registrar**: Wherever compraste `smarterbot.cl` (likely Namecheap, GoDaddy, IonOS, etc.)
- **Access**: https://[registrar-name].com → My Domains → smarterbot.cl → DNS Settings

### 1. Update Root Domain (@)

**Current**:
```
Type: A
Name: @ (or leave blank)
Value: 216.198.79.1
TTL: 3600
```

**Change to**:
```
Type: A
Name: @ (or leave blank)
Value: 89.116.23.167
TTL: 3600
```

### 2. Update www Subdomain

**Current** (if CNAME to Vercel):
```
Type: CNAME
Name: www
Value: 81c926cb1110b381.vercel-dns-017.com
TTL: 3600
```

**Change to**:
```
Type: A
Name: www
Value: 89.116.23.167
TTL: 3600
```

*(If it's already an A record, just change the value)*

### 3. Verify/Update api, ledger, biostack, monitoring, graph

**For each subdomain**, ensure it exists and points to `89.116.23.167`:

```
Type: A
Name: api | ledger | biostack | monitoring | graph
Value: 89.116.23.167
TTL: 3600
```

*(Create new records if they don't exist)*

---

## Verification Commands (Post-DNS Update)

After updating DNS records, DNS propagation takes **5-30 minutes**. Verify with:

```bash
# From your Mac (local machine)
dig smarterbot.cl +short
dig www.smarterbot.cl +short
dig api.smarterbot.cl +short
dig ledger.smarterbot.cl +short
dig biostack.smarterbot.cl +short

# All should return: 89.116.23.167

# Or use nslookup
nslookup smarterbot.cl
nslookup api.smarterbot.cl
```

**Expected output**:
```
89.116.23.167
89.116.23.167
89.116.23.167
```

---

## Caddy Configuration on VPS

Caddy is **already running** on the VPS and will automatically:
1. ✅ Detect the new DNS records
2. ✅ Request SSL certificates from Let's Encrypt
3. ✅ Serve HTTPS on ports 80/443
4. ✅ Route subdomains to appropriate microservices

**Caddy configuration file**: `/home/smarter/smarteros-brain/Caddyfile`

**Apply configuration**:
```bash
ssh smarter@89.116.23.167
cd ~/smarteros-brain
sudo systemctl reload caddy
# or
docker compose restart caddy  # if running in container
```

**Verify Caddy is running**:
```bash
ssh smarter@89.116.23.167
curl -v http://localhost:80/health
```

---

## Expected Behavior After DNS Fix

### 1. Domain Resolution ✅
```bash
$ dig smarterbot.cl +short
89.116.23.167
```

### 2. HTTP → HTTPS Redirect ✅
```bash
$ curl -i http://smarterbot.cl
HTTP/1.1 301 Moved Permanently
Location: https://smarterbot.cl/
```

### 3. HTTPS with Valid Certificate ✅
```bash
$ curl -I https://smarterbot.cl
HTTP/2 200 OK
Content-Length: ...
```

### 4. API Endpoint ✅
```bash
$ curl https://api.smarterbot.cl/health
{"status":"ok","version":"1.0.0"}
```

### 5. Routing Brain (Fee Optimization) ✅
```bash
$ curl -X POST https://api.smarterbot.cl/routing \
  -H "Content-Type: application/json" \
  -d '{"amount":250000,"payment_method":"credit_card"}'
{"processor":"stripe","fee":1.9,"savings":0.6}
```

### 6. Monitoring Dashboard ✅
```
https://monitoring.smarterbot.cl → Grafana
https://graph.smarterbot.cl → Neo4j Browser
https://ledger.smarterbot.cl → LedgerBrain API
```

---

## Troubleshooting

### DNS not updating after 30 minutes?
1. Clear local DNS cache:
   ```bash
   # macOS
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemctl restart systemd-resolved
   ```

2. Force check with Google nameserver:
   ```bash
   dig @8.8.8.8 smarterbot.cl +short
   ```

3. Check propagation globally: https://www.whatsmydns.net/?domain=smarterbot.cl

### HTTPS certificate not working?
1. Verify Caddy is running and has correct Caddyfile:
   ```bash
   docker logs smarteros-caddy  # if containerized
   sudo journalctl -u caddy -f  # if systemd service
   ```

2. Check Let's Encrypt rate limits: https://letsencrypt.org/docs/rate-limits/

3. Force certificate renewal:
   ```bash
   caddy renew --force
   ```

### Port 80/443 still not responding?
1. Check firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. Verify ports are open:
   ```bash
   ss -tlnp | grep -E ':80|:443'
   ```

3. Check if Caddy process is running:
   ```bash
   ps aux | grep caddy
   ```

---

## Timeline to Demo-Ready

1. **Update DNS** (your registrar) — **5 minutes**
2. **DNS propagates globally** — **5-30 minutes**
3. **Verify with `dig`** — **1 minute**
4. **Test endpoints** — **2 minutes**
5. **Demo ready** — **Within 30-40 minutes total**

---

## For the Demo

Once DNS is live, you can show:

```bash
# Terminal 1: Show domain resolves
$ dig smarterbot.cl +short
89.116.23.167

# Terminal 2: Show HTTPS certificate
$ curl -I https://smarterbot.cl
HTTP/2 200 OK
content-type: application/json
date: Sat, 15 Mar 2026 12:00:00 GMT

# Terminal 3: Test fee optimization
$ curl -X POST https://api.smarterbot.cl/routing \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_rut": "12345678-9",
    "amount": 500000,
    "payment_method": "credit_card"
  }'

Response:
{
  "original_fee": 2.5,
  "optimized_fee": 1.9,
  "savings": 3000,
  "processor": "stripe",
  "confidence": 0.94
}
```

**Boom.** Cliente entra, ve el dominio, ve HTTPS verde, ve el cerebro optimizando fees en tiempo real.

---

**Status**: Ready to deploy. Just waiting for DNS update.
