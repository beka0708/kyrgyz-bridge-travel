# Запуск на сервере

Всё, что здесь описано, проверено локально в Docker (`DOMAIN=localhost`): сборка, HTTPS, сжатие,
кеш, `/healthz/`, скрытая админка, бэкап и проверка дампа. На сервере остаётся пройти шаги ниже.

## 0. Что купить и подготовить вместе с заказчиком

| Что | Рекомендация |
|---|---|
| VPS | Ubuntu 24.04, 2 vCPU, 2–4 ГБ RAM, 40 ГБ SSD (Hetzner, DigitalOcean, Timeweb и т. п.) |
| Домен | у любого регистратора; доступ к DNS-записям |
| Почта для заявок | ящик заказчика, куда будут приходить письма |
| Brevo | бесплатный аккаунт (300 писем в день), SMTP-ключ |
| Остальное | номер WhatsApp, ID Google Analytics, ключ OpenRouteService, при желании ключи Turnstile и Sentry |

## 1. DNS

У регистратора домена создать записи:

```
A     example.com      → IP сервера
A     www.example.com  → IP сервера
```

Для Brevo добавить записи SPF/DKIM/DMARC, которые Brevo покажет в разделе «Senders & IP → Domains»:
без них письма о заявках попадут в спам.

## 2. Сервер

```bash
ssh root@IP
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
adduser deploy && usermod -aG docker deploy
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

Дальше работаем под `deploy`.

## 3. Код и настройки

```bash
sudo mkdir -p /opt/kg-tours && sudo chown deploy: /opt/kg-tours
git clone <репозиторий> /opt/kg-tours
cd /opt/kg-tours
cp deploy/.env.prod.example .env
nano .env    # DOMAIN, SITE_URL, ALLOWED_HOSTS, SECRET_KEY, POSTGRES_PASSWORD, EMAIL_URL, ADMIN_URL...
```

Сгенерировать ключи:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # SECRET_KEY
python3 -c "import secrets;print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
```

## 4. Запуск

```bash
cd /opt/kg-tours/deploy
docker compose -f compose.prod.yml --env-file ../.env up -d --build
docker compose -f compose.prod.yml --env-file ../.env ps          # все сервисы Up / healthy
curl -s https://example.com/healthz/                               # ok
```

Если npm качается медленно, в `.env` добавить `NPM_REGISTRY=https://registry.npmmirror.com`.

Администратор:

```bash
docker compose -f compose.prod.yml --env-file ../.env exec app python manage.py createsuperuser
```

Админка: `https://example.com/<ADMIN_URL>` (не `/admin/` — он отдаёт 404).

Перенести контент с демо-стенда не нужно: заказчик заполняет туры в админке сам.
Демо-данные (`seed_demo`) на проде **не запускать**.

## 5. Cron (бэкапы, повтор писем)

```bash
mkdir -p /opt/kg-tours/backups
crontab /opt/kg-tours/deploy/crontab.example
```

Бэкап: каждый день в 03:30, хранятся 7 дней (`/opt/kg-tours/backups`). Рекомендуется копировать
папку вне сервера (rclone в облако или скачивать раз в неделю).

## 6. Проверка после запуска

- [ ] Сайт открывается по https, http и www перенаправляют на https://example.com
- [ ] Заявка с сайта приходит на почту (не в спам), «Ответить» пишет туристу
- [ ] В админке: туры, редактор маршрута (по тропам — нужен `ORS_API_KEY`)
- [ ] `https://example.com/robots.txt` разрешает индексацию, `/sitemap.xml` с туром
- [ ] Google Search Console: добавить сайт, отправить sitemap
- [ ] GA4: ID в админке → «Контакты и SEO» → «SEO и аналитика»; события видны в «Realtime»
- [ ] Lighthouse (мобильный) по главной и туру: на локальной проверке 100 / 99
- [ ] Когда ясно, что все поддомены на HTTPS: `SECURE_HSTS_INCLUDE_SUBDOMAINS=true`

## Обновление сайта

```bash
cd /opt/kg-tours && git pull
cd deploy && docker compose -f compose.prod.yml --env-file ../.env up -d --build
```

Миграции применяются автоматически при старте контейнера.

## Восстановление из бэкапа

```bash
cd /opt/kg-tours/deploy
C="docker compose -f compose.prod.yml --env-file ../.env"
# база
$C exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < ../backups/db-ДАТА.dump
# фото
$C exec -T app tar -C /app/media -xzf - < ../backups/media-ДАТА.tar.gz
$C exec app python manage.py warm_images
```

## Локальная проверка боевой сборки

```bash
cat > /tmp/kt-prod-test.env <<EOF
DOMAIN=localhost
HTTP_PORT=8080
HTTPS_PORT=8443
SITE_URL=https://localhost:8443
ALLOWED_HOSTS=localhost
CSRF_TRUSTED_ORIGINS=https://localhost:8443
DEBUG=false
SECRET_KEY=local-test-only
POSTGRES_PASSWORD=local-test-only
EMAIL_URL=consolemail://
ROBOTS_DISALLOW_ALL=true
ENV_FILE=/tmp/kt-prod-test.env
EOF
cd deploy && ENV_FILE=/tmp/kt-prod-test.env docker compose -f compose.prod.yml --env-file /tmp/kt-prod-test.env up -d --build
# https://localhost:8443 (самоподписанный сертификат)
```
