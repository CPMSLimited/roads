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
- Left-side filter uses `Route` and `Condition` instead of `State`.
- Speed-vs-distance graph auto-loads the first segment returned by the active filter.
- If the current filter returns no segments, the page shows `No segments found for the selected filter.`
- Segment ordering uses:
  - parent route
  - segment trailing two-digit suffix (numeric)
  - `id` tie-breaker
- Sub-segment ordering uses:
  - parent route
  - parent segment trailing two-digit suffix (numeric)
  - parent segment id
  - sub-segment trailing suffix (numeric)
  - `id` tie-breaker

## 5) Library
Sections:
- Road inventory
- Reports
- Technical guide
- User guide

Notes:
- Shared page title behavior implemented as `Library` across sections.
- Technical and user guides are rendered via shared guide template logic.

### Road inventory interactions
- Segment rows no longer open the editor directly.
- A compact edit icon beside each segment checkbox opens the segment edit modal.
- Clicking a segment row expands it inline as an accordion.
- Only one segment can stay expanded at a time.
- Expanded segment rows load sub-segments on demand.

### Inline sub-segment workspace
- Expanded sub-segment tables show:
  - checkbox
  - edit icon
  - sub-segment code
  - start point
  - end point
  - distance
- The inline sub-segment edit modal currently updates:
  - start point
  - end point
- Sub-segment distance remains visible in the table but is read-only in the modal.
- Selecting sub-segments reveals a local `Delete` action above the expanded sub-segment table.
- Confirmed delete removes the selected sub-segments and then renumbers the remaining rows so codes stay contiguous.

### Data hygiene and constraints
- Segment codes are standardized to end in two digits.
- Segment code max length is now 16 characters.
- Shared list ordering ignores the middle portion of the code and prioritizes route plus the final two-digit suffix.
- Duplicate sub-segment imports are collapsed during upload so repeated coordinate/data rows are not created.
- Sub-segment position ceiling is now 35, with duplicate-cleanup and renumbering support in the migration path.

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
- Top navigation is fixed site-wide.
- Library and Engineering left navigation panes are fixed on desktop and scroll independently from the main content area.

## 7) Data import/sync utilities

### Route details sync command
- Command: `python manage.py sync_route_details`
- Reads route lines from template source and updates `Route.details`.
- Supports dry run and apply mode.

### Segment refresh services/tasks
- Queue refresh endpoint and Celery task for updating distances/speeds/status from Google API.
