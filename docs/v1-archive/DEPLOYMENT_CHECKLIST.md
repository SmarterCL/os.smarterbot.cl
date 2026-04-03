# 🚀 SmarterOS Brain - DEPLOYMENT CHECKLIST

## Phase 1: Pre-Deployment (DNS Ready + VPS Prepared)

### DNS Configuration ✅ CRITICAL

- [ ] **Go to registrar** (Namecheap, GoDaddy, IonOS, etc.)
- [ ] **Update A Record (@/root)**: `216.198.79.1` → `89.116.23.167`
- [ ] **Update A Record (www)**: Vercel alias → `89.116.23.167` (remove CNAME)
- [ ] **Verify api.smarterbot.cl**: Already pointing to `89.116.23.167` ✓
- [ ] **Create new A records**:
  - [ ] ledger.smarterbot.cl → 89.116.23.167
  - [ ] biostack.smarterbot.cl → 89.116.23.167
  - [ ] monitoring.smarterbot.cl → 89.116.23.167
  - [ ] graph.smarterbot.cl → 89.116.23.167
- [ ] **Wait for propagation** (5-30 minutes)
- [ ] **Verify DNS**: Run `./validate-dns.sh` from your Mac

### VPS Cleanup & Preparation

- [ ] **SSH into VPS**: `ssh smarter@89.116.23.167`
- [ ] **Check disk usage**: `df -h /` (target: <60%)
- [ ] **Clean up old containers**:
  ```bash
  docker system prune -a --volumes
  docker image prune -a
  ```
- [ ] **Stop non-essential containers** (N8N, Odoo, Chatwoot, etc.):
  ```bash
  cd ~/smarteros-agents
  docker compose down
  ```
- [ ] **Verify free disk space**: Need >30GB
- [ ] **Check memory**: `free -h` (should have 2GB+ available)

### Repository Setup

- [ ] **Clone SmarterOS Brain repo**:
  ```bash
  cd ~
  git clone https://github.com/SmarterCL/os.smarterbot.cl.git smarteros-brain
  cd smarteros-brain
  ```
- [ ] **Copy environment file**: `cp .env.example .env`
- [ ] **Edit .env** with production values:
  ```bash
  nano .env
  # Update: DATABASE_URL, NEO4J_PASSWORD, STRIPE_API_KEY, etc.
  ```

---

## Phase 2: Infrastructure Deployment

### Database Setup

- [ ] **Start PostgreSQL**:
  ```bash
  docker compose up -d postgres
  sleep 10
  ```
- [ ] **Initialize database schema**:
  ```bash
  docker compose exec postgres psql -U smarteros -d smarteros < init.sql
  ```
- [ ] **Verify tables created**:
  ```bash
  docker compose exec postgres psql -U smarteros -d smarteros \
    -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
  ```
- [ ] **Enable pgvector**:
  ```bash
  docker compose exec postgres psql -U smarteros -d smarteros \
    -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
  ```

### Graph Database (Neo4j)

- [ ] **Start Neo4j**:
  ```bash
  docker compose up -d neo4j
  sleep 15
  ```
- [ ] **Verify connectivity**:
  ```bash
  docker compose exec neo4j cypher-shell -u neo4j -p smarteros "RETURN 1;"
  ```
- [ ] **Access Neo4j Browser**: http://localhost:7474
  - [ ] Login: neo4j / smarteros
  - [ ] Run: `:play intro` (verify it works)

### Cache (Redis)

- [ ] **Start Redis**:
  ```bash
  docker compose up -d redis
  ```
- [ ] **Verify connectivity**:
  ```bash
  docker compose exec redis redis-cli ping
  ```

### Full Stack Deployment

- [ ] **Deploy all services**:
  ```bash
  docker compose up -d
  ```
- [ ] **Verify all containers running**:
  ```bash
  docker compose ps
  # Should show: orchestrator, biostack, routing-brain, ledger-brain, 
  #              memory, postgres, neo4j, redis, prometheus, grafana
  ```
- [ ] **Check container health**:
  ```bash
  docker compose ps --format "table {{.Names}}\t{{.Status}}"
  ```

---

## Phase 3: Caddy Configuration & SSL

### Configure Reverse Proxy

- [ ] **Verify Caddyfile**: `/home/smarter/smarteros-brain/Caddyfile`
- [ ] **Update Caddyfile** with your domains (already done ✓)
- [ ] **Start/Reload Caddy**:
  ```bash
  docker compose up -d caddy
  # or if running as systemd service:
  sudo systemctl reload caddy
  ```
- [ ] **Verify Caddy is running**:
  ```bash
  docker compose ps caddy
  ```

### SSL Certificate Provisioning

- [ ] **Let's Encrypt will auto-provision** HTTPS certificates
- [ ] **Wait 2-5 minutes** for Let's Encrypt to issue certs
- [ ] **Test HTTPS locally**:
  ```bash
  curl -k https://localhost/health
  ```
- [ ] **Check certificate**:
  ```bash
  echo | openssl s_client -servername smarterbot.cl -connect localhost:443 2>/dev/null | openssl x509 -noout -dates
  ```

---

## Phase 4: Validation & Testing

### DNS Validation

- [ ] **Run validation script** from your Mac:
  ```bash
  bash validate-dns.sh
  ```
- [ ] **Manual checks**:
  ```bash
  dig smarterbot.cl +short       # Should return 89.116.23.167
  dig api.smarterbot.cl +short   # Should return 89.116.23.167
  ```

### Endpoint Testing

- [ ] **Test Orchestrator (root domain)**:
  ```bash
  curl https://smarterbot.cl/health
  # Expected: {"status":"ok","version":"1.0.0"}
  ```

- [ ] **Test RoutingBrain (fee optimization)**:
  ```bash
  curl -X POST https://api.smarterbot.cl/routing \
    -H "Content-Type: application/json" \
    -d '{
      "merchant_rut": "12345678-9",
      "amount": 500000,
      "payment_method": "credit_card"
    }'
  # Expected: {"processor":"stripe","fee":1.9,"savings":3000}
  ```

- [ ] **Test LedgerBrain**:
  ```bash
  curl https://ledger.smarterbot.cl/health
  # Expected: 200 OK
  ```

- [ ] **Test BioStack**:
  ```bash
  curl https://biostack.smarterbot.cl/health
  # Expected: 200 OK
  ```

### Dashboard Access

- [ ] **Grafana** (monitoring): https://monitoring.smarterbot.cl
  - [ ] Default login: admin / smarteros
  - [ ] Verify Prometheus datasource is connected
  - [ ] Check system metrics dashboard

- [ ] **Neo4j Browser** (graph DB): https://graph.smarterbot.cl
  - [ ] Login: neo4j / smarteros
  - [ ] Run sample query: `MATCH (m:Merchant) RETURN count(m);`

### Performance Checks

- [ ] **Check container memory usage**:
  ```bash
  docker stats --no-stream
  # All containers should use <2GB total
  ```

- [ ] **Check disk space**:
  ```bash
  df -h /
  # Should have >20GB free
  ```

- [ ] **View logs for errors**:
  ```bash
  docker compose logs orchestrator | tail -50
  docker compose logs routing-brain | tail -50
  ```

---

## Phase 5: Production Hardening

### Security

- [ ] **Update environment secrets** in `.env`:
  ```bash
  JWT_SECRET=$(openssl rand -base64 32)
  API_KEY_MASTER=$(openssl rand -base64 32)
  ENCRYPTION_KEY=$(openssl rand -base64 32)
  ```

- [ ] **Firewall configuration**:
  ```bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw allow 7687/tcp  # Neo4j (if external access needed)
  sudo ufw enable
  ```

- [ ] **Disable root login**:
  ```bash
  sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
  sudo systemctl restart ssh
  ```

### Monitoring & Logs

- [ ] **Configure log rotation**:
  ```bash
  sudo tee /etc/docker/daemon.json > /dev/null <<EOF
  {
    "log-driver": "json-file",
    "log-opts": {
      "max-size": "10m",
      "max-file": "3"
    }
  }
  EOF
  sudo systemctl restart docker
  ```

- [ ] **Set up Prometheus scraping** (already configured in docker-compose.yml ✓)
- [ ] **Configure Grafana alerts** (optional but recommended)

### Backups

- [ ] **PostgreSQL backup**:
  ```bash
  docker compose exec postgres pg_dump -U smarteros smarteros > backup_$(date +%s).sql
  ```

- [ ] **Neo4j backup**:
  ```bash
  docker compose exec neo4j neo4j-admin database dump neo4j > neo4j_backup_$(date +%s).dump
  ```

- [ ] **Setup automated backups** (cron job):
  ```bash
  # Add to crontab: crontab -e
  0 2 * * * cd ~/smarteros-brain && docker compose exec postgres pg_dump -U smarteros smarteros > /backups/postgres_$(date +\%Y\%m\%d).sql
  0 3 * * * cd ~/smarteros-brain && docker compose exec neo4j neo4j-admin database dump neo4j > /backups/neo4j_$(date +\%Y\%m\%d).dump
  ```

---

## Phase 6: Demo Ready! 🎉

### Pre-Demo Verification

- [ ] **All endpoints responding**: ✅
- [ ] **HTTPS with valid certificate**: ✅ (green lock)
- [ ] **DNS propagated globally**: ✅
- [ ] **Monitoring dashboard live**: ✅
- [ ] **Database initialized**: ✅

### Demo Script

```bash
# Show domain + HTTPS
curl -I https://smarterbot.cl

# Show fee optimization in action
curl -X POST https://api.smarterbot.cl/routing \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_rut": "99999999-9",
    "amount": 1000000,
    "payment_method": "credit_card"
  }'

# Show real-time fraud detection
curl https://biostack.smarterbot.cl/health

# Show accounting ledger
curl https://ledger.smarterbot.cl/ledger/latest

# Open Grafana dashboard
# https://monitoring.smarterbot.cl
```

---

## Rollback Plan (If Something Goes Wrong)

1. **DNS rollback**: Point `smarterbot.cl` back to `216.198.79.1` (takes 30 min to propagate)
2. **Container rollback**: `docker compose down && git checkout HEAD~1`
3. **Database rollback**: Restore from backup SQL
4. **Full revert**: `docker system prune -a` and redeploy from GitHub

---

## Post-Deployment Monitoring

- [ ] **Daily**: Check `docker stats` for memory/CPU
- [ ] **Weekly**: Review logs for errors
- [ ] **Monthly**: Update certificates, test backups
- [ ] **Quarterly**: Security patches, dependency updates

---

## Support & Escalation

- **SSH Issue**: `ssh -v smarter@89.116.23.167` (debug connection)
- **DNS Issue**: https://www.whatsmydns.net/?domain=smarterbot.cl
- **Certificate Issue**: Check Caddy logs: `docker logs smarteros-caddy`
- **Database Issue**: Check PostgreSQL logs: `docker compose logs postgres`
- **Container Crash**: Check health: `docker compose ps`

---

**Total Deployment Time**: ~45 minutes (including DNS propagation wait)

**Status**: Production-ready once DNS is updated at registrar.
