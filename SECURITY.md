# 🔒 Security Policy

## Reporting a Vulnerability

Report security issues via: smarterbotcl@gmail.com

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

### Pre-commit Secret Scan

Before pushing, run:
```bash
grep -rn "7631[0-9]*:AA\|eyJhbGciOi\|sk-\|ghp_" . --include="*.py" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.md" --include="*.sh" | grep -v ".git/" | grep -v SECURITY.md
```
If any results appear, remove the secret before committing.
