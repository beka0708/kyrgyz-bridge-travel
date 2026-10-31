# Kyrgyz Tours — сайт турагентства

Django-монолит: страницы, админка (django-unfold) и REST API со Swagger.
Архитектура и решения: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), ТЗ: `docs/TZ.docx`, макеты: `docs/design/`.

## Быстрый старт

Нужны: [uv](https://docs.astral.sh/uv/), Docker, Node.js 22+.

```bash
cp .env.example .env          # если .env ещё нет
make db                       # PostgreSQL 17 в Docker на localhost:5440
make migrate
make superuser
make seed                     # демо-туры, отзывы, FAQ (фото-заглушки)
make front-install && make front-build   # карта маршрута и редактор в админке
make dev                      # http://localhost:8010
```

| Адрес | Что |
|---|---|
| `/admin/` | админка для заказчика (на русском) |
| `/api/docs/` | Swagger |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI-схема |
| `/`, `/tours/`, `/tours/<slug>/` | страницы-заглушки до этапа фронта |

## Фронтенд

Vue-островки (карта маршрута, редактор в админке) собираются Vite в `backend/static/dist/`.

- Разовая сборка: `make front-build`, затем **перезапустить Django** — django-vite читает манифест при старте.
- Разработка с hot reload: `VITE_DEV_MODE=true` в `.env` и `make front-dev` рядом с `make dev`.

## Карты

MapLibre + OpenFreeMap (векторная карта), рельеф из открытых данных AWS, слой «Topo» — OpenTopoMap.
Ключей не нужно; адреса провайдеров меняются переменными `MAP_*` в `.env`.

- 3D-рельеф: админка → «Контакты и SEO» → вкладка «Карта»: выключен / только компьютеры / везде.
- Линия маршрута дня строится при сохранении в админке: прямые линии, по дорогам, по пешим тропам
  (OpenRouteService, нужен бесплатный ключ `ORS_API_KEY` с account.heigit.org) или из GPX.

## Деплой

Docker-сборка для сервера (Postgres + gunicorn + Caddy с автоматическим HTTPS), бэкапы и cron —
в [`deploy/`](deploy/README.md). Пошаговая инструкция запуска и проверка боевой сборки
локально — в [deploy/README.md](deploy/README.md).

## SEO, аналитика, скорость

- **Картинки:** при сохранении в админке в фоне создаются WebP 160/480/960/1600 px и превью
  1200×630 JPEG для соцсетей (`media/cache/`). Для уже загруженных фото:
  `cd backend && uv run python manage.py warm_images`.
- **SEO:** title/description/canonical/Open Graph на каждой странице, JSON-LD (`TravelAgency`,
  `TouristTrip`, `BreadcrumbList`), `/sitemap.xml`, `/robots.txt`. На тестовом сервере —
  `ROBOTS_DISALLOW_ALL=true`, чтобы его не индексировали. Адреса берутся из `SITE_URL`.
- **GA4:** ID вписывается в админке («Контакты и SEO» → «SEO и аналитика»). Без ID скрипты Google
  не грузятся. Consent Mode v2: для ЕС/UK/CH аналитика только после «Accept» в cookie-баннере
  (баннер видят посетители с европейским часовым поясом). События: `view_item`,
  `whatsapp_click`, `telegram_click`, `generate_lead`.
- **Антиспам формы:** Cloudflare Turnstile включается ключами `TURNSTILE_SITE_KEY` и
  `TURNSTILE_SECRET_KEY` в `.env`.

## Команды

| Команда | Что делает |
|---|---|
| `make test` | pytest (поднимает БД, если не запущена) |
| `make lint` / `make fmt` | ruff: проверка / автоисправление |
| `make check` | `manage.py check` + валидация OpenAPI-схемы |
| `make migrations` | создать миграции |
| `make front-build` / `make front-dev` | сборка фронта / Vite с hot reload |
| `cd backend && uv run python manage.py resend_inquiries` | переотправить письма о заявках (для cron) |
| `cd backend && uv run python manage.py warm_images` | создать WebP-варианты для всех загруженных фото |

## API v1

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/v1/tours/?tour_type=solo\|group&is_featured=true` | список опубликованных туров |
| GET | `/api/v1/tours/{slug}/` | тур: дни, галерея, включено/не включено/снаряжение, SEO, ссылка WhatsApp |
| GET | `/api/v1/tours/{slug}/route/` | точки и линии по дням + границы для карты |
| GET | `/api/v1/settings/` | контакты, мессенджеры, соцсети, настройки карты |
| GET | `/api/v1/guides/`, `reviews/?tour=<slug>`, `faq/`, `partners/`, `gallery/`, `stats/` | контент |
| POST | `/api/v1/inquiries/` | заявка: лимит 5/час с IP, honeypot `website`, Turnstile |
| POST | `/api/v1/admin/routes/build/`, `/admin/routes/gpx/` | только сотрудники: предпросмотр линии маршрута |
