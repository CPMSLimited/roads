# API Reference (Current)

Base prefix: `/api/` (for DRF endpoints under `all_roads/api/urls.py`)

## 1) List all segments
- Method: `GET`
- Path: `/api/all_segments/`
- Handler: `all_roads.api.views.all_segments_view`
- Response: serialized Segment records (`SegmentSerializer`, `fields='__all__'`)

## 2) Queue refresh
- Method: `POST`
- Path: `/api/update-segments/queue/`
- Handler: `all_roads.api.views.queue_refresh`
- Request JSON (optional):

```json
{
  "codes": ["F100LAS1", "F102RIV2"]
}
```

- Response JSON:

```json
{
  "task_id": "<celery-task-id>"
}
```

## 3) Task status
- Method: `GET`
- Path: `/api/tasks/<uuid:task_id>/`
- Handler: `all_roads.api.views.task_status`
- Response JSON:
  - `task_id`
  - `state`
  - `result` (if successful)
  - `error` (if failed)

## Website JSON endpoints (non-DRF but API-like)

## 4) Road inventory route details
- Method: `GET`
- Path: `/road-inventory/route-details/`
- Query params:
  - `route` (required)
- Handler: `website.views.road_inventory_route_details`
- Response JSON:
  - `summary` object
  - `segments` array

## 5) Segment code search
- Method: `GET`
- Path: `/segments/search/`
- Query params:
  - `q` (min length 2)
- Handler: `website.views.segment_code_search`

## 6) Road condition subsegments
- Method: `GET`
- Path: `/road-condition/subsegments/`
- Query params:
  - `segment` (required)
- Handler: `website.views.road_condition_subsegments`

## 7) Road condition save draft
- Method: `POST`
- Path: `/road-condition/save-draft/`
- Handler: `website.views.road_condition_save_draft`
- Creates draft defects for selected sub-segments where eligible.

## Auth and permissions notes
- Some endpoints currently use `AllowAny` and should be reviewed for production hardening if public write access is not intended.
- JWT authentication is configured globally in DRF settings, but endpoint-level permission decorators control openness.

## API operational recommendations
- Use queue refresh endpoint for production updates.
- Poll task status endpoint for completion and summary.
- Add rate and permission controls before exposing write-capable endpoints publicly.
