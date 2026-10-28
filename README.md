# Kyrgyz Tours — сайт турагентства

Django-монолит: страницы, админка (django-unfold) и REST API со Swagger.
Архитектура и решения: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), ТЗ: `docs/TZ.docx`, макеты: `docs/design/`.

## Быстрый старт

Нужны: [uv](https://docs.astral.sh/uv/), Docker. (Node.js понадобится на этапе фронта.)

```bash
cp .env.example .env          # если .env ещё нет
make db                       # PostgreSQL 17 в Docker на localhost:5434
make migrate
make superuser
make seed                     # демо-туры, отзывы, FAQ (фото-заглушки)
make dev                      # http://localhost:8000
```

| Адрес | Что |
|---|---|
| `/admin/` | админка для заказчика (на русском) |
| `/api/docs/` | Swagger |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI-схема |
| `/`, `/tours/`, `/tours/<slug>/` | страницы-заглушки до этапа фронта |

## Команды

| Команда | Что делает |
|---|---|
| `make test` | pytest (поднимает БД, если не запущена) |
| `make lint` / `make fmt` | ruff: проверка / автоисправление |
| `make check` | `manage.py check` + валидация OpenAPI-схемы |
| `make migrations` | создать миграции |
| `cd backend && uv run python manage.py resend_inquiries` | переотправить письма о заявках (для cron) |

## API v1

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/v1/tours/?tour_type=solo\|group&is_featured=true` | список опубликованных туров |
| GET | `/api/v1/tours/{slug}/` | тур: дни, галерея, включено/не включено/снаряжение, SEO, ссылка WhatsApp |
| GET | `/api/v1/tours/{slug}/route/` | точки и линии по дням + границы для карты |
| GET | `/api/v1/settings/` | контакты, мессенджеры, соцсети |
| GET | `/api/v1/guides/`, `reviews/?tour=<slug>`, `faq/`, `partners/`, `gallery/`, `stats/` | контент |
| POST | `/api/v1/inquiries/` | заявка: лимит 5/час с IP, honeypot `website`, Turnstile |
