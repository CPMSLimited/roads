# Features and Workflows

## 1) Landing
- FERMA-branded entry page.
- Navigation to Inventory, Motorability, Condition, Library, Engineering Admin.

## 2) Road Inventory
Primary use case: route and segment inventory exploration.

### Main sections
- KPI strip above map
- Map/table view section
- Right side cards:
  - `Segment summary`
  - `Segment details` with:
    - Segment Identity table
    - Segment Characteristics table

### Current behavior highlights
- Filters are mutually exclusive in page logic (road OR route OR state).
- Route row selection loads details via AJAX endpoint:
  - `GET /road-inventory/route-details/?route=<route_code>`
- Summary includes:
  - Route
  - Length (sum of segment distances)
  - Start point/End point derived from first/last segment by index ordering
  - Passes through (`Route.details`)
  - Number of segments
- Start/End display fallback chain for name:
  - Address FK name -> Segment name -> Segment state -> `-`
- Point display format:
  - `Name (Lat, Lon)` with fixed decimal precision

## 3) Road Motorability
Primary use case: evaluate motorability performance and segment status distribution.

### Main sections
- KPI strip (length/routes/segments/no data)
- Status KPI strip (Good/Tolerable/Intolerable/Failed)
- Map/table view
- Right side cards:
  - `Motorability summary`
  - `Segments under investigation or repair`

### Investigation/repair table behavior
- One row per segment
- Filter-aware (uses page filter context)
- Source: `Defect` records where workflow status is not `repair_complete`
- Columns:
  - Segment (segment code)
  - Status (human-readable workflow status)
- Sort order:
  - Segment index/code ordering

## 4) Road Condition
Primary use case: operate on sub-segment condition records and create draft defect records.

### Key endpoints
- `POST /road-condition/save-draft/`
- `GET /road-condition/subsegments/?segment=<code>`

### Behavior
- Creates defect drafts only for eligible sub-segments.
- Prevents duplicate active records per sub-segment.

## 5) Library
Sections:
- Road inventory
- Reports
- Technical guide
- User guide

Notes:
- Shared page title behavior implemented as `Library` across sections.
- Technical and user guides are rendered via shared guide template logic.

## 6) Engineering Admin
Workflow tabs/pages:
- Root Cause Analysis
- Physical Inspection
- Solution Design
- Approvals
- Overview/History variants

### Workflow progression (conceptual)
`draft -> rca -> physical_inspection -> solution_design -> approved/rejected -> repair_ongoing -> repair_complete`

### Recent UI update
- Priority controls/labels removed from Approvals and engineering-admin summary tables.

## 7) Data import/sync utilities

### Route details sync command
- Command: `python manage.py sync_route_details`
- Reads route lines from template source and updates `Route.details`.
- Supports dry run and apply mode.

### Segment refresh services/tasks
- Queue refresh endpoint and Celery task for updating distances/speeds/status from Google API.
