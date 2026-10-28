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
