# Architecture

## System overview
CPMS FERMA is a Django monolith with server-rendered templates, domain APIs, and background workers.

```text
Browser
  -> Nginx
    -> Gunicorn (Django: roads.wsgi)
      -> website app (template views)
      -> all_roads app (domain models + API)
      -> PostgreSQL
      -> Redis (Celery broker/result)

Celery Worker
  -> all_roads.tasks.refresh_segments_task
    -> all_roads.services.refresh_segments_from_google
      -> Google Distance Matrix API
      -> PostgreSQL updates
```

## Code boundaries
- `roads/`
  - project-level URLs
  - split settings (`settings/base.py`, `settings/local.py`, `settings/production.py`)
  - WSGI/ASGI and Celery bootstrap
- `website/`
  - page-level routes and application workflows
  - inventory/motorability/condition pages
  - engineering-admin workflows
  - library pages
- `all_roads/`
  - domain models (`Road`, `Route`, `Segment`, `SubSegment`, `Defect`, workflow models)
  - DRF endpoints for segment refresh/status
  - services for Google API refresh
  - Celery tasks and management commands

## Data model map (high-level)

```text
Road (1) ----- (N) Route (1) ----- (N) Segment (1) ----- (N) SubSegment
                         |                         |
                         |                         +-- start_point/end_point -> Address
                         +-- start_point/end_point -> Address

SubSegment (1) ----- (N) Defect
Defect (1) ----- (N) RootCauseAnalysis (1) ----- (N) RootCauseDetail
Defect (1) ----- (N) PhysicalInspection (1) ----- (N) PhysicalInspectionAnalysis
PhysicalInspectionAnalysis (1) ----- (N) PhysicalInspectionCharacteristic

Library: document records linked by workflow context (defect/inspection/etc.)
```

## Request flow examples

### 1) Road inventory page
1. `GET /road-inventory/` -> `website.views.road_inventory`
2. Builds filter-aware queryset of `Segment`
3. Computes KPI metrics and right-panel summary/detail datasets
4. Renders `website/templates/website/road_inventory.html`
5. Table row click triggers AJAX to `/road-inventory/route-details/`

### 2) Road condition save-draft
1. User selects sub-segments and submits
2. `POST /road-condition/save-draft/`
3. Backend creates `Defect` draft for eligible sub-segments (non-terminal)
4. Returns JSON with created/blocked/not-found counts

### 3) Segment refresh via background job
1. `POST /api/update-segments/queue/` (optional segment codes)
2. Returns Celery task ID
3. Worker calls Google Distance Matrix API
4. Updates `Segment` fields: distance/travel_time/avg_speed/status/start/end address

## Settings architecture
- Split settings package is authoritative:
  - `roads.settings.base`
  - `roads.settings.local`
  - `roads.settings.production`
- Production inserts WhiteNoise middleware and uses manifest static storage.
- A legacy `roads/settings.py` exists and should be treated as legacy/backward artifact.

## Static files architecture
- App static source: `website/static/website/...`
- Collected static: `STATIC_ROOT = BASE_DIR/staticfiles`
- Production serving path: `/static/...`
- Common failure mode: stale app process serving old/empty static artifacts after deployment; restart Gunicorn after `collectstatic`.

## Background processing
- Broker/result backend: Redis (`REDIS_URL`)
- Task module: `all_roads/tasks.py`
- Core service implementation: `all_roads/services.py`
- Recommended operation: queue refreshes for long-running updates instead of synchronous endpoint loops.

## Security posture (production)
- HTTPS redirect on
- secure cookies on
- HSTS enabled
- host allow-list configured
- CSRF trusted origins configured for production domains

## Known architectural risks
- Very large `website/views.py` (many concerns in one module).
- Potential confusion from coexistence of split settings package and legacy `roads/settings.py` file.
- Requirements file appears incomplete for full reproducible setup.
