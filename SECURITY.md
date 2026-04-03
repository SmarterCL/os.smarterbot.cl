# 🔒 Security Policy

## Reporting a Vulnerability

Report security issues via: smarterbotcl@gmail.com

## GitGuardian Integration

This project uses [GitGuardian](https://dashboard.gitguardian.com/workspace/866485/) 
for automated secret detection.

### Pre-commit Hook

Every commit is scanned for secrets automatically:
```bash
# Install pre-commit hook
cp .git/hooks/pre-commit .git/hooks/pre-commit.bak  # backup existing
# Hook is auto-installed — runs ggshield on staged files
```

### CI Scan Script

```bash
# Scan any repository
/usr/local/bin/scan-secrets.sh /path/to/repo

# Scan specific repo
scan-secrets.sh /root/os.smarterbot.cl
scan-secrets.sh /root/bolt-os
```

### Manual Scan

```bash
export GITGUARDIAN_API_KEY=$(cat /opt/smarter-os/.env.gg)
/var/www/smarter_latam/venv/bin/ggshield secret scan path . --recursive
```

## Secrets Management

All secrets must be stored as environment variables or GitHub Secrets.
Never commit actual tokens, keys, or passwords to this repository.

### Required Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `DB_PASSWORD` | Database password |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GITGUARDIAN_API_KEY` | GitGuardian API key |

### Pre-commit Secret Scan

Before pushing, run:
```bash
/usr/local/bin/scan-secrets.sh
```
If any secrets are found, remove them before committing.
