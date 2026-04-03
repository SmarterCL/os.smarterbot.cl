# Deployment Guide - SmarterOS Brain v1.0

## VPS Setup (Ubuntu 24.04 LTS)

### Prerequisites
- Ubuntu 24.04 LTS
- Docker & Docker Compose
- Git
- SSH access to VPS

### 1. SSH into VPS

```bash
ssh smarter@89.116.23.167
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/SmarterCL/os.smarterbot.cl.git smarteros-brain
cd smarteros-brain
```

### 3. Environment Setup

```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

### 4. Database Initialization

```bash
# PostgreSQL with pgvector extension
docker compose up -d postgres
sleep 10
docker compose exec postgres psql -U smarteros -d smarteros < init.sql
```

### 5. Neo4j Setup

```bash
docker compose up -d neo4j
# Access at http://localhost:7474
# Login: neo4j / smarteros
# Load initial graph data (see NEO4J_RUT_REAL_QUERIES.cypher)
```

### 6. Full Stack Deployment

```bash
docker compose up -d
```

Verify all containers:
```bash
docker compose ps
```

### 7. Health Check

```bash
curl http://localhost:3000/health
curl http://localhost:3002/routing
curl http://localhost:3003/ledger
```

### 8. DNS Configuration

Update DNS A records to point to VPS:
- `smarterbot.cl` → 89.116.23.167
- `api.smarterbot.cl` → 89.116.23.167
- `www.smarterbot.cl` → 89.116.23.167

### 9. Caddy Reverse Proxy

Configure Caddy for HTTPS + subdomain routing:

```
smarterbot.cl, www.smarterbot.cl {
  reverse_proxy localhost:3000
}

api.smarterbot.cl {
  reverse_proxy localhost:3002
}
```

### 10. System Optimization

#### Disk Cleanup
```bash
docker system prune -a
docker image prune -a
# Target: <60% disk usage (need 30GB+ free)
```

#### Memory Management
```bash
# Monitor memory usage
docker stats --no-stream
# Stop non-essential containers
docker stop <container_name>
```

#### Logs Rotation
```bash
# Configure logrotate for Docker
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

#### Linux Swap
```bash
# Add swap if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Monitoring & Operations

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator

# Real-time streaming
docker compose logs -f --tail=100 routing-brain
```

### Performance

```bash
# Resource usage
docker stats

# Disk usage
df -h /
docker system df

# Memory analysis
free -h
docker compose exec postgres psql -U smarteros -d smarteros -c 'SELECT pg_database_size(current_database());'
```

### Database Backup

```bash
# PostgreSQL
docker compose exec postgres pg_dump -U smarteros smarteros > backup_$(date +%s).sql

# Neo4j
docker compose exec neo4j neo4j-admin database dump neo4j > neo4j_backup_$(date +%s).dump
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs <service>

# Restart service
docker compose restart <service>

# Full restart
docker compose down
docker compose up -d
```

### Out of Memory (OOM)

```bash
# Check memory usage
free -h
docker stats

# Increase swap
sudo fallocate -l 8G /swapfile
sudo swapon /swapfile

# Reduce container memory limits (if needed)
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       memory: 512M
```

### Disk Full

```bash
# Check disk
df -h /

# Clean up
docker system prune -a --volumes
rm -rf /var/log/docker/*.log*

# Delete old backups
rm -f backup_*.sql
```

### Database Connection Issues

```bash
# Test PostgreSQL
docker compose exec postgres psql -U smarteros -d smarteros -c 'SELECT 1;'

# Test Neo4j
docker compose exec neo4j cypher-shell -u neo4j -p smarteros "RETURN 1;"

# Test Redis
docker compose exec redis redis-cli ping
```

## CI/CD Pipeline

GitHub Actions workflow located in `.github/workflows/deploy.yml`:
- Runs on push to main
- Builds Docker images
- Runs tests
- Pushes to registry
- Deploys to VPS (via Dokploy webhook)

## API Documentation

See `API.md` for endpoint specifications.

## Support

Issues: https://github.com/SmarterCL/os.smarterbot.cl/issues
