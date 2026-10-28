BACK = cd backend && uv run

.PHONY: db dev migrate migrations superuser seed test lint fmt shell check

db:            ## start PostgreSQL in Docker
	docker compose up -d --wait db

dev: db        ## run Django dev server
	$(BACK) python manage.py runserver

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
