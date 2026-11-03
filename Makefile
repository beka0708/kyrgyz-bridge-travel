BACK = cd backend && uv run
# Web port; override with: make dev PORT=9000
PORT ?= 8010

.PHONY: db dev migrate migrations superuser seed test lint fmt shell check front-install front-dev front-build

db:            ## start PostgreSQL in Docker
	docker compose up -d --wait db

dev: db        ## run Django dev server
	$(BACK) python manage.py runserver 127.0.0.1:$(PORT)

migrate:
	$(BACK) python manage.py migrate

migrations:
	$(BACK) python manage.py makemigrations

superuser:
	$(BACK) python manage.py createsuperuser

seed:          ## demo tours and content for local work
	$(BACK) python manage.py seed_demo

test: db
	$(BACK) pytest

lint:
	$(BACK) ruff check . && $(BACK) ruff format --check .

fmt:
	$(BACK) ruff check --fix . && $(BACK) ruff format .

check:
	$(BACK) python manage.py check && $(BACK) python manage.py spectacular --validate --fail-on-warn --file /dev/null

shell:
	$(BACK) python manage.py shell

front-install: ## npm packages for frontend/
	cd frontend && npm install

front-dev:     ## Vite with hot reload; set VITE_DEV_MODE=true in .env
	cd frontend && npm run dev

front-build:   ## typecheck + build into backend/static/dist (restart Django after)
	cd frontend && npm run build

# ------------------------------------------------------------------ server (preview / production)
# [laptop] targets run on your computer and talk to the server over SSH;
# [server] targets run on the server inside /opt/kg-tours (see deploy/README.md).
SERVER ?= deploy@kyrgyzbridgetravel.com
APP_DIR ?= /opt/kg-tours
BRANCH ?= main
PROD = cd deploy && docker compose -f compose.prod.yml --env-file ../.env

.PHONY: secrets preview-password server-setup server-clone deploy deploy-photos ssh \
	prod-env prod-up prod-ps prod-logs prod-restart prod-down prod-superuser prod-demo \
	prod-shell prod-backup prod-cron

secrets:          ## fresh SECRET_KEY, POSTGRES_PASSWORD and ADMIN_URL for .env
	@python3 -c "import secrets as s; print('SECRET_KEY=' + s.token_urlsafe(50)); print('POSTGRES_PASSWORD=' + s.token_urlsafe(24)); print('ADMIN_URL=manage-' + s.token_hex(4) + '/')"

preview-password: ## PREVIEW_PASSWORD_HASH line for .env: make preview-password PASSWORD=...
	@test -n "$(PASSWORD)" || { echo "usage: make preview-password PASSWORD=..."; exit 1; }
	@echo "PREVIEW_PASSWORD_HASH=$$(docker run --rm caddy:2-alpine caddy hash-password --plaintext '$(PASSWORD)' | base64 | tr -d '\n')"

server-setup:     ## [laptop] one-time setup of a fresh server as root: make server-setup IP=1.2.3.4
	@test -n "$(IP)" || { echo "usage: make server-setup IP=<server ip>"; exit 1; }
	ssh root@$(IP) 'bash -s' < deploy/server-setup.sh

server-clone:     ## [laptop] clone the repo on the server: make server-clone REPO=git@github.com:org/repo.git
	@test -n "$(REPO)" || { echo "usage: make server-clone REPO=<git url> [BRANCH=main]"; exit 1; }
	ssh $(SERVER) 'test -d $(APP_DIR)/.git || git clone -b $(BRANCH) $(REPO) $(APP_DIR)'

deploy:           ## [laptop] update the server to the latest $(BRANCH) and rebuild
	ssh $(SERVER) 'cd $(APP_DIR) && git fetch -q && git checkout -q $(BRANCH) && git pull --ff-only -q && make prod-up'

deploy-photos:    ## [laptop] copy demo photos to the server (preview only)
	ssh $(SERVER) 'mkdir -p $(APP_DIR)/demo/photos'
	rsync -az demo/photos/ $(SERVER):$(APP_DIR)/demo/photos/

ssh:              ## [laptop] open a shell on the server
	ssh $(SERVER)

prod-env:         ## [server] create .env from deploy/.env.prod.example (once)
	@if [ -f .env ]; then echo ".env exists, not touched"; else cp deploy/.env.prod.example .env && echo "created .env: fill it in with nano .env"; fi

prod-up:          ## [server] build and start, or update, the site
	$(PROD) up -d --build --remove-orphans
	$(PROD) ps

prod-ps:          ## [server] status of the containers
	$(PROD) ps

prod-logs:        ## [server] follow logs (Ctrl+C to stop)
	$(PROD) logs -f --tail=100

prod-restart:     ## [server] restart without rebuilding (e.g. after editing .env)
	$(PROD) up -d --force-recreate

prod-down:        ## [server] stop the site (data stays)
	$(PROD) down

prod-superuser:   ## [server] create an admin account
	$(PROD) exec app python manage.py createsuperuser

prod-demo:        ## [server] fill a PREVIEW with demo tours and photos (refuses on a public site)
	@grep -q '^SITE_ACCESS=preview' .env || { echo "refusing: demo data only when SITE_ACCESS=preview"; exit 1; }
	$(PROD) exec app python manage.py demo_fill
	$(PROD) exec app python manage.py warm_images

prod-shell:       ## [server] Django shell
	$(PROD) exec app python manage.py shell

prod-backup:      ## [server] database + photos backup now (also runs nightly from cron)
	./deploy/backup.sh

prod-cron:        ## [server] install nightly backups and email retries
	mkdir -p backups && crontab deploy/crontab.example && crontab -l
