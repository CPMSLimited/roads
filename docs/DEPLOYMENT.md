# Deployment Guide (DigitalOcean, Ubuntu)

This guide is aligned with your current production model:
- Ubuntu droplet
- Nginx reverse proxy
- Gunicorn for Django
- PostgreSQL
- Redis + Celery
- static/media from Django paths

## 1) Server prerequisites
- Python 3.10+
- PostgreSQL
- Redis
- Nginx
- systemd

## 2) Clone and environment setup
```bash
cd /home/appleveil
git clone <repo-url> ferma
cd ferma
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create env file (or export vars):
```bash
cp .env.example roads/.env
# Edit values in roads/.env
```

## 3) Database and migrations
```bash
python manage.py migrate --settings=roads.settings.production
```

## 4) Static files
```bash
python manage.py collectstatic --noinput --settings=roads.settings.production
```

If CSS appears stale after deploy, restart Gunicorn.

## 5) Gunicorn systemd service (example)
`/etc/systemd/system/gunicorn.service`

```ini
[Unit]
Description=gunicorn daemon for cpms_ferma
After=network.target

[Service]
User=appleveil
Group=www-data
WorkingDirectory=/home/appleveil/ferma
Environment="DJANGO_SETTINGS_MODULE=roads.settings.production"
ExecStart=/home/appleveil/ferma/venv/bin/gunicorn roads.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

Commands:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

## 6) Nginx site config (example)
`/etc/nginx/sites-available/cpmsferma`

```nginx
server {
    listen 80;
    server_name cpmsferma.com www.cpmsferma.com;

    location /static/ {
        alias /home/appleveil/ferma/staticfiles/;
    }

    location /media/ {
        alias /home/appleveil/ferma/media/;
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

Enable/reload:
```bash
sudo ln -s /etc/nginx/sites-available/cpmsferma /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 7) Celery worker (systemd example)
`/etc/systemd/system/celery.service`

```ini
[Unit]
Description=Celery Worker for CPMS FERMA
After=network.target redis.service

[Service]
Type=simple
User=appleveil
Group=www-data
WorkingDirectory=/home/appleveil/ferma
Environment="DJANGO_SETTINGS_MODULE=roads.settings.production"
ExecStart=/home/appleveil/ferma/venv/bin/celery -A roads worker -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

## 8) Deployment checklist
1. Pull code.
2. Activate venv.
3. Install/upgrade deps.
4. Run migrations.
5. Run `collectstatic`.
6. Restart gunicorn.
7. Reload nginx.
8. Restart celery if changed.
9. Smoke test key pages and static assets.

## 9) Post-deploy verification
```bash
curl -I https://cpmsferma.com/static/website/css/style.css
curl -I https://cpmsferma.com/
```

Expected CSS check:
- HTTP 200
- non-zero `Content-Length`

## 10) Common pitfall encountered
- Symptom: CSS URL returns 200 but with `Content-Length: 0`.
- Cause: stale process/static state after deployment.
- Fix: rerun collectstatic and restart gunicorn.
