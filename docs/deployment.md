# Deployment

## Database

The project reads `DATABASE_URL` and falls back to local SQLite when it is
unset, so a fresh clone runs with no configuration. Set it to point at a real
server:

```
# MySQL
DATABASE_URL=mysql://user:password@host:3306/dbname

# Postgres
DATABASE_URL=postgres://user:password@host:5432/dbname
```

URL-encode any `@ : / ? #` in the password, or the URL parses wrongly.

### MySQL specifics

`mysqlclient` is the driver (in `requirements.txt`). Three settings are applied
automatically in `settings/base.py` when the engine is MySQL:

| Setting | Why |
| --- | --- |
| `charset=utf8mb4` | MySQL's "utf8" is a 3-byte subset that cannot store emoji or much CJK text. |
| `sql_mode=STRICT_TRANS_TABLES` | Without it MySQL silently truncates over-long values instead of raising. |
| `ssl_mode` (default `REQUIRED`) | The connection is encrypted. |

> **A trap worth knowing.** Use `ssl_mode`, never an empty `OPTIONS["ssl"] = {}`
> — mysqlclient ignores the empty dict, and an unencrypted connection makes
> MySQL 8 reject `caching_sha2_password` logins. It reports that as
> **"Access denied for user ..."**, which reads like wrong credentials rather
> than a TLS problem.

`REQUIRED` encrypts without verifying the server certificate, which suits a
managed host presenting a self-signed one. To authenticate the server as well,
set `DATABASE_SSL_CA` to a CA bundle and raise `DATABASE_SSL_MODE=VERIFY_CA`.
`DISABLED` turns TLS off.

Connections are reused between requests (`DATABASE_CONN_MAX_AGE`, default 60s)
because a MySQL handshake over a network link is expensive;
`CONN_HEALTH_CHECKS` discards ones the server has already dropped.

### First deploy to an empty database

```bash
python manage.py migrate          # schema + the category/course taxonomy
python manage.py createsuperuser  # the admin login
python manage.py seed_srmmba      # optional: the SRM B-School content
```

Running the test suite creates and drops a `test_<dbname>` database, so the
database user needs `CREATE` privileges — or point `DATABASE_URL` at SQLite
when running tests.


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

# Uploads on S3 instead of the local disk - see "Media storage on S3" below.
USE_S3=True
AWS_STORAGE_BUCKET_NAME=<bucket>
AWS_S3_REGION_NAME=ap-south-1
AWS_ACCESS_KEY_ID=<key id>
AWS_SECRET_ACCESS_KEY=<secret>
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

## Media storage on S3

Uploaded images (event galleries, blog covers, faculty portraits, CKEditor
uploads) default to the local disk under `MEDIA_ROOT`. That works, but it ties
the content to one server's filesystem and puts image traffic through Django.
Setting `USE_S3=True` moves every upload to an S3 bucket instead.

The switch is resolved in `mbu_backend/settings/storage.py`; nothing in the
models, serializers or admin changes, because they all go through Django's
`FileField.url`.

### 1. Create the bucket

Region should match the application server (`ap-south-1` for an India
deployment). Keep **ACLs disabled** (the default "Bucket owner enforced") and
switch **Block all public access** off — the bucket policy below is what
actually grants access, and it only grants reads under `media/`.

### 2. Bucket policy

Attach this under *Permissions → Bucket policy*, replacing the bucket name:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadMedia",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR-BUCKET/media/*"
    }
  ]
}
```

Read-only, and scoped to the `media/` prefix. Nobody can upload, delete or list
the bucket without credentials.

### 3. IAM user for the application

Create a programmatic-access-only user with exactly these permissions — never
reuse an administrator key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::YOUR-BUCKET"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR-BUCKET/*"
    }
  ]
}
```

Then create an access key for it (*Security credentials → Create access key →
Application running outside AWS*). The secret is displayed once.

### 4. Configure the application

```bash
USE_S3=True
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Two optional values:

| Variable | Use |
| --- | --- |
| `AWS_S3_CUSTOM_DOMAIN` | CloudFront distribution or CNAME serving the bucket. Image URLs switch to it automatically. |
| `AWS_S3_ENDPOINT_URL` | Only for S3-compatible providers — Cloudflare R2, DigitalOcean Spaces, MinIO. Leave empty for real AWS. |

Install the dependencies (already pinned in `requirements.txt`):

```bash
pip install -r requirements.txt
```

### 5. Move the existing uploads

Flipping the flag only redirects *new* uploads. Files already on disk must be
copied up, or every existing image 404s:

```bash
python manage.py sync_media_to_s3 --dry-run   # preview
python manage.py sync_media_to_s3             # upload
```

The command skips files already present in the bucket, so it is safe to re-run.
Use `--overwrite` to force a re-upload.

### 6. Verify

```bash
python manage.py shell -c "from django.core.files.storage import default_storage; print(default_storage.url('events/gallery/example.jpg'))"
```

The printed URL should be an `https://` address with no `?X-Amz-Signature=`
query string, and opening an existing image in a browser should return it
rather than an *Access Denied* XML error.

### Notes

- **Static files stay local.** WhiteNoise already serves them well from the
  application container; only media moves to S3.
- **Next.js frontends** must list the bucket (or CDN) host under
  `images.remotePatterns` in `next.config.js`, otherwise `next/image` refuses
  to load them.
- **Backups get simpler.** With media on S3, the `media/` tarball in the backup
  section below is replaced by S3 versioning or a scheduled
  `aws s3 sync s3://your-bucket/media/ ./media-backup/`.

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
- [ ] Media directory writable by the app user and backed up — or
      `USE_S3=True` with the bucket policy, IAM user and `sync_media_to_s3` done
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
