# CPMS FERMA

Comprehensive Pavement Management System (CPMS) for FERMA.

This repository contains a Django application for:
- road inventory visualization and route/segment metadata
- road motorability and status analytics
- road condition workflows
- engineering administration workflows (root cause, physical inspection, solution design, approvals)
- library/document records
- background refresh jobs for segment/sub-segment distance/speed/status data

## Quick start (short version)
1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables from `.env.example`.
4. Run migrations.
5. Start Django.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example roads/.env
python manage.py migrate
python manage.py runserver
```

## Settings profile
This project uses split settings under `roads/settings/`:
- `roads.settings.local`
- `roads.settings.production`

Use explicitly when running commands:

```bash
python manage.py runserver --settings=roads.settings.local
python manage.py collectstatic --noinput --settings=roads.settings.production
```

## Documentation index
- [Architecture](docs/ARCHITECTURE.md)
- [Features and Workflows](docs/FEATURES.md)
- [API](docs/API.md)
- [Deployment (DigitalOcean)](docs/DEPLOYMENT.md)
- [Operations Runbook](docs/OPERATIONS.md)
- [Project Status Report](docs/PROJECT_STATUS_REPORT.md)
- [Environment Template](.env.example)

## Main app structure
- `roads/` Django project config, URLs, settings, WSGI/ASGI, Celery bootstrap
- `website/` web routes, template rendering, workflow logic
- `all_roads/` domain models, API endpoints, services/tasks, admin, migrations
- `website/templates/website/` main UI templates
- `website/static/website/` frontend assets

## Notes
- A legacy file `roads/settings.py` exists, but active configuration is the split settings package (`roads/settings/`).
- Static files in production are collected into `staticfiles/`.
