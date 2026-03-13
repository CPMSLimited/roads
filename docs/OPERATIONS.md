# Operations Runbook

## Useful commands

### Django checks
```bash
python manage.py check --settings=roads.settings.production
python manage.py showmigrations --settings=roads.settings.production
```

### Static files
```bash
python manage.py collectstatic --noinput --settings=roads.settings.production
ls -l /home/appleveil/ferma/staticfiles/website/css/style.css
curl -I https://cpmsferma.com/static/website/css/style.css
```

### Services
```bash
sudo systemctl status gunicorn
sudo systemctl restart gunicorn
sudo systemctl status nginx
sudo systemctl reload nginx
sudo systemctl status celery
sudo systemctl restart celery
```

### Logs
```bash
journalctl -u gunicorn -n 200 --no-pager
journalctl -u nginx -n 200 --no-pager
journalctl -u celery -n 200 --no-pager
tail -n 200 /home/appleveil/ferma/django-error.log
```

## Troubleshooting matrix

## 1) Styling missing in production
Checks:
1. Page source contains `<link href="/static/website/css/style.css">`
2. `staticfiles/website/css/style.css` exists and non-zero size.
3. `curl -I` returns non-zero content-length.

Fixes:
- `collectstatic`
- restart gunicorn
- reload nginx

## 2) `staticfiles.W004` warning
Message: static dir in `STATICFILES_DIRS` does not exist.

Action:
- ensure settings include only existing static dirs (already implemented in base settings).

## 3) Celery tasks stuck
Checks:
- Redis reachable
- celery worker running
- task status endpoint state

Actions:
- restart celery
- verify `REDIS_URL`
- inspect worker logs for API rate limits/timeouts

## 4) Map data not updating
Checks:
- `segments_map_data` endpoint response
- segment coordinates present
- background refresh completed successfully

## 5) 500 errors from views
Checks:
- `django-error.log`
- recent code changes in `website/views.py`
- migrations applied for model changes

## Database operation cautions
- Always back up DB before destructive updates.
- For production schema changes:
  1. deploy code
  2. run migrations
  3. restart services

## Rollback strategy (minimum)
1. keep previous release commit hash
2. revert to previous code
3. rerun `collectstatic`
4. restart gunicorn/celery
5. if migration caused issue, restore DB backup or apply reversible migration

## Security operation checks
- Ensure production settings are used in production commands.
- Confirm HTTPS redirect and HSTS active.
- Review open endpoints and permission decorators periodically.
