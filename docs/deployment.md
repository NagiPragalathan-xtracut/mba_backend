# Deployment

Running the backend in production.

## What changes

`DJANGO_ENV=production` loads `mbu_backend/settings/production.py`, which:

- turns `DEBUG` off;
- **refuses to start** without an explicit `DJANGO_SECRET_KEY` — there is no
  insecure fallback;
- enables HSTS, SSL redirect, secure and HTTP-only cookies, `X-Frame-Options:
  DENY` and `nosniff`;
- serves JSON only (the browsable API is a development aid).

## Environment

Create `.env` on the server, or set real environment variables:

```dotenv
DJANGO_ENV=production
DJANGO_SECRET_KEY=<50+ random characters>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.example.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://api.example.edu

DATABASE_URL=postgres://mbu:<password>@localhost:5432/mbu

SITE_BASE_URL=https://www.example.edu
SITE_NAME=Mohan Babu University

CORS_ALLOWED_ORIGINS=https://www.example.edu
CORS_ALLOW_ALL_ORIGINS=False

DJANGO_TIME_ZONE=Asia/Kolkata
MEDIA_ROOT=/var/www/mbu/media
STATIC_ROOT=/var/www/mbu/staticfiles
```

Generate the secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

> `SITE_BASE_URL` is the **public website** address, not the API's — canonical
> URLs, Open Graph images and schema.org data are built from it. Getting it
> wrong produces SEO tags pointing at the wrong host.

## PostgreSQL

SQLite is fine for development, not for production. Install a driver:

```bash
pip install psycopg[binary]
```

Create the database and set `DATABASE_URL`:

```sql
CREATE DATABASE mbu;
CREATE USER mbu WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE mbu TO mbu;
```

Nothing in the code is SQLite-specific — the partial unique constraint on
featured event images works on PostgreSQL too.

## Deploy steps

```bash
pip install -r requirements.txt
export DJANGO_ENV=production

python manage.py check --deploy      # must be clean
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser     # first deploy only
```

Then run it:

```bash
gunicorn mbu_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

A systemd unit:

```ini
[Unit]
Description=MBU Backend
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/srv/mbu_backend
Environment="DJANGO_ENV=production"
EnvironmentFile=/srv/mbu_backend/.env
ExecStart=/srv/mbu_backend/.venv/bin/gunicorn mbu_backend.wsgi:application \
          --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

## nginx

WhiteNoise handles static files, but nginx should serve uploaded media directly
and must allow large enough uploads (the app's own limit is 10 MB per image):

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.edu;

    client_max_body_size 12M;

    location /media/ {
        alias /var/www/mbu/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`X-Forwarded-Proto` matters: production settings trust it to detect HTTPS.

## Checklist

- [ ] `DJANGO_SECRET_KEY` set, unique to this deployment, never committed
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` lists only the real hostnames
- [ ] `CORS_ALLOW_ALL_ORIGINS=False`, with the real frontend in `CORS_ALLOWED_ORIGINS`
- [ ] `SITE_BASE_URL` points at the public website
- [ ] PostgreSQL, not SQLite
- [ ] TLS terminated, HTTP redirected
- [ ] `python manage.py check --deploy` clean
- [ ] `collectstatic` run
- [ ] Media directory writable by the app user and backed up
- [ ] `.env` is `chmod 600` and excluded from version control
- [ ] API tokens issued per client, ready to rotate

## Backups

Two things matter:

```bash
pg_dump -Fc mbu > mbu-$(date +%F).dump          # database
tar czf media-$(date +%F).tar.gz /var/www/mbu/media/   # uploads
```

A database dump without the media directory restores content whose images are
all broken — back up both, on the same schedule.

## The MCP server in production

It does not need to run on the server. Point it at the deployed API from
wherever it runs:

```dotenv
MBU_API_BASE_URL=https://api.example.edu
MBU_API_TOKEN=<token issued for that environment>
```

Issue a **separate token per environment** so a development key never grants
production access, and rotate with
`python manage.py create_api_token --username mcp-bot --rotate`.

## Upgrading

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test tests          # optional but recommended
systemctl restart mbu-backend
```

Take a database dump before migrating anything that changes a schema.
