# Standalone Media Processing Engine

Standalone FastAPI + SQLite + Docker media processing system. No TIPIZ or external website integration.

## Phase 1 includes

- FastAPI backend
- SQLite database
- Admin login with bcrypt password hash + signed session token
- API key authentication
- Job creation/list/detail/retry/cancel
- Simple processing queue
- Minimal responsive admin dashboard
- Docker + Caddy reverse proxy
- System health/resources/storage/telegram status endpoints

## Quick start

```bash
cp .env.example .env
# edit .env
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"
# put the hash in ADMIN_PASSWORD_HASH

docker compose up -d --build
```
