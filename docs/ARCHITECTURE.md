# Архитектура: сайт туров по Кыргызстану

Статус: черновик, 2026-10-26. Решения ниже приняты; открытые вопросы — в конце.

## 1. Принцип

**Модульный монолит на Django.** Одно приложение отдаёт:

- HTML-страницы (SEO, быстрый первый экран на телефоне);
- админку для заказчика (django-unfold);
- небольшой REST API (`/api/v1/`, Swagger) — для Vue-островков, формы заявки и на будущее
  (Telegram-бот, CRM, мобильное приложение из «второго этапа»).

Фронт собирается Vite в статические файлы, которые Django отдаёт как обычную статику.
Один Docker-образ, один деплой, один сервер.

```
                 ┌──────────────────────── VPS ────────────────────────┐
 браузер ──443──▶│ Caddy (HTTPS, gzip)                                 │
                 │  ├─ /static/*  → файлы с диска (собранный Vite)     │
                 │  ├─ /media/*   → файлы с диска (фото из админки)    │
                 │  └─ остальное  → gunicorn :8000                     │
                 │                   Django                            │
                 │                   ├─ страницы (шаблоны + островки)  │
                 │                   ├─ /admin/  (unfold)              │
                 │                   └─ /api/v1/ (DRF + Swagger)       │
                 │                        │                            │
                 │                   PostgreSQL                        │
                 └────────────────────────┼────────────────────────────┘
                                          ├─▶ Brevo (письма о заявках)
                                          ├─▶ сервис маршрутов (1 раз при сохранении дня)
                                          └─▶ Sentry (ошибки)
  браузер ─▶ тайлы карты, GA4, Turnstile — напрямую со своих CDN
```

## 2. Стэк

| Слой | Выбор | Почему |
|---|---|---|
| Язык / пакеты | Python 3.13, `uv` | Быстро, lock-файл |
| Фреймворк | Django 5.2 LTS | Поддержка до 04.2028 |
| API | Django REST Framework + drf-spectacular | Swagger `/api/docs/`, схема OpenAPI |
| БД | PostgreSQL 17 | JSONField для геометрии маршрута, без PostGIS |
| Админка | django-unfold | Аккуратный интерфейс «из коробки» |
| Шаблоны | Django templates + django-cotton | Компоненты `<c-tour-card>` — переиспользуемые блоки для адаптива |
| Стили | Tailwind CSS v4, mobile-first | Дизайн-токены из макета (цвета, Unbounded/Manrope) |
| Мелкая интерактивность | Alpine.js | Меню, вкладки, аккордеон FAQ, фильтр, вкладки дней на мобилке |
| Сложные блоки | Vue 3 + TypeScript (островки) | Карта маршрута на сайте и редактор маршрута в админке — один код |
| Сборка фронта | Vite + django-vite | HMR в разработке, хэшированные файлы в проде |
| Карусель | Swiper | Хиты сезона, галерея |
| Анимации | `motion` + CSS | Появление при скролле; выключаются при `prefers-reduced-motion` |
| Карта | MapLibre GL JS 6 + OpenFreeMap + рельеф AWS Terrain + OpenTopoMap | Бесплатно, без ключей; адреса в `MAP_*`, код за адаптером `frontend/src/map/provider.ts` |
| Фото | Pillow → WebP, 3 размера (`srcset`) | Скорость на мобилке |
| Почта | django-anymail + Brevo | Письма не уходят в спам; 300/день бесплатно |
| Антиспам | honeypot + Cloudflare Turnstile + rate limit | Без «выбери светофоры» |
| SEO | sitemaps, robots, Open Graph, JSON-LD (`TouristTrip`) | Поля SEO в админке |
| Аналитика | GA4 + Consent Mode v2 + vanilla-cookieconsent | Баннер для Европы |
| Ошибки | Sentry (free) | Узнаём о падениях раньше заказчика |
| Тесты / качество | pytest-django, factory-boy, ruff, pre-commit | |
| Деплой | Docker Compose: app + db + caddy | HTTPS автоматически |

Чего сознательно **нет**: Celery/Redis (трафик маленький, письма шлём после коммита,
неотправленные — переотправляет команда по cron), PostGIS, SPA/Next/Nuxt, мультиязычность
(но строки в шаблонах сразу оборачиваем в `{% translate %}` — второй язык потом дешевле).

## 3. Структура папок

```
тур/
├── backend/
│   ├── pyproject.toml, uv.lock
│   ├── manage.py
│   ├── config/
│   │   ├── settings/        base.py · dev.py · prod.py · test.py
│   │   ├── urls.py          страницы + /admin/ + /api/
│   │   ├── api_urls.py      роутер /api/v1/ + Swagger
│   │   └── wsgi.py, asgi.py
│   ├── apps/
│   │   ├── core/            базовые модели-миксины, SiteSettings, главная, context processors, SEO-хелперы
│   │   ├── tours/           туры, дни, маршрут, галерея; страницы списка и тура; sitemap; JSON-LD
│   │   │   └── services/    routing.py (линия маршрута), gpx.py (импорт трека), images.py
│   │   ├── content/         гиды, отзывы, FAQ, партнёры, «живые кадры»
│   │   └── inquiries/       заявки, антиспам, уведомления на почту
│   │   (в каждом app: models · admin · views · api/{serializers,views,urls} · tests/)
│   ├── templates/
│   │   ├── base.html
│   │   ├── pages/           home · tour_list · tour_detail · 404 · 500
│   │   ├── partials/        header · footer · whatsapp_button · cookie_banner
│   │   ├── cotton/          компоненты: tour_card · button · section_title · day_card …
│   │   ├── admin/           переопределения unfold (виджет редактора маршрута)
│   │   └── emails/          письмо о новой заявке
│   └── static/              своё статичное (иконки, шрифты); vite кладёт сборку в static/dist/
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json
│   └── src/
│       ├── entries/         main.ts (Alpine, Swiper, анимации) · route-map.ts · route-editor.ts (админка)
│       ├── components/      RouteMap.vue · RouteEditor.vue · DayGallery.vue
│       ├── map/             адаптер провайдера карты (MapLibre / Google — меняется в одном месте)
│       ├── lib/             api-клиент, аналитика (события GA4), утилиты
│       └── styles/          main.css (Tailwind, токены, шрифты)
├── deploy/
│   ├── Dockerfile           multi-stage: node собирает фронт → python-образ
│   ├── compose.prod.yml
│   ├── Caddyfile
│   └── backup.sh            pg_dump + media по cron
├── docs/
│   ├── ARCHITECTURE.md      этот файл
│   ├── TZ.docx
│   └── design/              макеты, PDF, фото-референсы
├── compose.yml              dev: только PostgreSQL
├── Makefile                 make dev · test · lint · migrate · build
├── .env.example
└── README.md
```

## 4. Модель данных

```
SiteSettings (singleton)   телефон, WhatsApp, email для заявок, соцсети, счётчики (лет, туров, гостей…)

Tour ──< TourDay ──< TourDayImage
 │          └─ waypoints: JSON [{lat, lng, name, kind}]   ← точки, поставленные кликом
 │             track: JSON GeoJSON LineString             ← линия, считается 1 раз при сохранении
 │             track_source: routed | manual | gpx
 │             gpx_file (необязательно)
 ├──< TourImage (галерея)
 ├──< TourListItem  kind: included | excluded | gear, text, order
 └──< Review (необязательно привязан к туру)

Tour: title, slug, type (solo|group), short_description, description, how_to_get_there,
      price_from, currency, duration_days, difficulty (easy|moderate|hard),
      group_size_min/max, season_from/to (месяцы), cover, is_published, is_featured (хиты),
      order, seo_title, seo_description, og_image

Guide · FAQ · Partner · GalleryPost (вместо ленты Instagram через API — картинка + ссылка)

Inquiry: name, email, contact (телефон/мессенджер), tour (FK, null), date_from/to, people,
         comment, status (new|in_progress|done|spam), notified_at, ip, user_agent, utm/referrer
```

Общие миксины в `core`: `TimeStamped`, `Orderable` (сортировка перетаскиванием в админке),
`Publishable`, `SEOFields`.

## 5. API v1 (Swagger: `/api/docs/`)

| Метод | URL | Для чего |
|---|---|---|
| GET | `/api/v1/tours/?type=solo\|group` | список (карусели, фильтр) |
| GET | `/api/v1/tours/{slug}/` | тур целиком |
| GET | `/api/v1/tours/{slug}/route/` | дни + точки + линии для карты |
| GET | `/api/v1/settings/` | контакты, WhatsApp, счётчики |
| GET | `/api/v1/reviews/`, `/faq/`, `/guides/`, `/partners/` | контент |
| POST | `/api/v1/inquiries/` | заявка (throttle + Turnstile + honeypot) |
| POST | `/api/v1/admin/routes/build/` | только staff: построить линию по точкам |
| POST | `/api/v1/admin/routes/gpx/` | только staff: GPX → GeoJSON |

Чтение — публичное, только опубликованные туры. Страницы **не** ходят в API при рендере:
Django отдаёт HTML сам, а данные для островка кладёт в страницу через `json_script` —
без лишнего запроса и без «мигания».

## 6. Рендеринг и фронт

- Весь текст (описания дней, цены, FAQ) — в HTML от Django: поисковики и превью в мессенджерах
  видят всё без JS.
- JS «оживляет» готовую разметку: Alpine для простого, Vue-островок только для карты.
- Островок карты подгружается, когда блок близко к экрану (IntersectionObserver), — первый
  экран на телефоне не тянет библиотеку карт.
- Связь «день ↔ карта»: Alpine-разметка дней шлёт событие `route:day` → Vue-карта подсвечивает
  участок. Так один и тот же компонент карты работает в обоих раскладах.

### Страница тура: вариант A + мобилка

| Экран | Раскладка |
|---|---|
| ≥ 1024 px | **Вариант A**: список дней слева, карта `sticky` справа; активный день — по клику и по скроллу |
| < 1024 px | Вкладки дней сверху (горизонтальный скролл чипов), под ними карта ~45vh, фото, описание — по сути вариант B |

Данные и компоненты одни, меняется только CSS-раскладка. Заказчику показать оба на устройстве.

### Адаптив

- Mobile-first: верстаем от 390 px, потом расширяем.
- Проверяем на 360 · 390 · 768 · 1024 · 1440 px и на живых iPhone/Android.
- Фото: `<picture>` + WebP 480/960/1600 px + `sizes`, `loading="lazy"` везде кроме первого экрана.
- Цель: Lighthouse mobile ≥ 90 по Performance, SEO, Accessibility.

## 7. Карта и маршрут (провайдер решаем позже)

- Код карты за адаптером `frontend/src/map/` — смена провайдера не трогает остальное.
- Кандидат: **MapLibre GL JS + OpenFreeMap** (без ключа и лимитов) или MapTiler (бесплатный
  тариф); топо-подложка показывает тропы и рельеф. Google Maps — запасной вариант.
- Линия маршрута строится **один раз при сохранении дня** в админке, хранится в `TourDay.track`:
  - переезд по дороге → сервис маршрутов (например, OpenRouteService, бесплатный ключ);
  - треккинг → точки кликом (линия по точкам) или загрузка GPX от гида.
- Посетитель сайта никогда не вызывает платный/лимитный API маршрутов.

## 8. Заявки

1. Форма → `POST /api/v1/inquiries/` (или обычный POST без JS — форма работает и так).
2. Проверки: honeypot, Turnstile, лимит 5 заявок/час с IP.
3. Сохраняем в БД → после коммита письмо заказчику через Brevo.
4. Не ушло письмо — `notified_at` пустой, команда `resend_inquiries` по cron пробует снова;
   в админке видно все заявки и их статус.
5. GA4-событие `generate_lead`; клик по WhatsApp — событие `whatsapp_click` с названием тура.

## 9. Окружения и деплой

- **dev**: PostgreSQL в Docker (`compose.yml`, порт 5434), Django через `uv run`, Vite dev-сервер с HMR.
- **prod**: `deploy/compose.prod.yml` — `app` (gunicorn), `db`, `caddy`; volumes для БД, media, static.
- Секреты только в `.env` (в git — `.env.example`).
- Бэкап: `pg_dump` + архив media раз в сутки, хранить 7 копий (рекомендуем, даже если
  поддержка вне объёма).

## 10. Порядок работ

1. Скелет: репозиторий, `backend/`, settings, Docker для БД, ruff, pytest, Makefile.
2. Модели + админка (unfold) + миграции + фикстуры с тестовыми турами.
3. API + Swagger + тесты.
4. Редактор маршрута в админке (Vue-островок) — самое рискованное, делаем рано.
5. Фронт: токены и база → главная → список туров → страница тура → форма.
6. Адаптив и анимации, проверка на устройствах.
7. SEO, GA4, cookie-баннер, Lighthouse.
8. Деплой на сервер заказчика, передача доступов.

## 11. Открытые вопросы

- Язык сайта — английский? (влияет на тексты, не на архитектуру).
- Какие блоки главной оставляем: гиды, FAQ, партнёры, «живые кадры», счётчики.
- Почта для заявок, номер WhatsApp, домен — от заказчика.
