up:     ; docker compose up -d --build
down:   ; docker compose down
logs:   ; docker compose logs -f --tail=200
web:    ; docker compose logs -f web
worker: ; docker compose logs -f worker
ps:     ; docker compose ps
pull:   ; git pull && docker compose up -d --build