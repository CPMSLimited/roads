# website/views.py

from all_roads.models import Segment, Route, Road
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Sum, Count, Q, IntegerField, Max
from django.db.models.functions import Cast
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from .forms import UploadSegmentsForm
import csv
import io

# ---- Status buckets used for counts/mini-chart (hex codes) ----
STATUS_BUCKETS = {
    "good": {"codes": ["339933", "006600"]},         # Good (>=90 km/h)
    "tolerable": {"codes": ["00CC00", "FFFFCC"]},    # OK / Manageable
    "intolerable": {"codes": ["FF9966", "FF5050"]},  # Poor / Bad
    "failed": {"codes": ["FF0000", "666699"]},       # Worsen / No response
}

# ---- Pagination options (Point 5) ----
PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_OPTIONS = [25, 50, 100]

def landing(request):
    return render(request, "website/landing.html")

def uploads(request):
    if request.method == "POST":
        # Placeholder only — real behaviour to be added when you share details
        # uploaded_file = request.FILES.get("segment_file")
        return HttpResponse("Upload received (stub). Behaviour to be defined.")
    return render(request, "website/uploads.html")

# ---- Road Analysis with page-size selector + robust filter preservation (Point 5) ----

def road_analysis(request):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()

    # Query params (single active filter enforced for route/state)
    selected_route = request.GET.get("route") or ""
    selected_state = request.GET.get("state") or ""
    selected_segment = request.GET.get("segment") or ""  # new, preserved but no-op (for now)
    show_all = request.GET.get("show") == "all"

    # Enforce mutual exclusivity (route vs state); segment remains independent (no-op)
    if show_all:
        selected_route = ""
        selected_state = ""
        # selected_segment kept as-is
    elif selected_route:
        selected_state = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_route = ""
        qs = qs.filter(state=selected_state)

    # Aggregates for metrics
    agg = qs.aggregate(total_length=Sum("distance"), total_segments=Count("id"))
    total_length = (agg["total_length"] or Decimal("0.00")).quantize(Decimal("0.01"))
    total_segments = agg["total_segments"] or 0

    # Counts per status bucket (for mini-chart)
    counts = {k: qs.filter(status__in=v["codes"]).count() for k, v in STATUS_BUCKETS.items()}

    # Options for selects
    routes = Route.objects.only("route").order_by("route")
    states = (
        Segment.objects.exclude(state="")
        .order_by("state")
        .values_list("state", flat=True)
        .distinct()
    )

    # NEW: options for the "Select segment" dropdown (no-op for now)
    # Using distinct codes; cap to 300 to keep the UI light. Adjust later as needed.
    segments_for_filter = list(
        Segment.objects.order_by("code").values_list("code", flat=True).distinct()[:300]
    )

    # ----- Page size -----
    try:
        page_size = int(request.GET.get("page_size") or PAGE_SIZE_DEFAULT)
        if page_size not in PAGE_SIZE_OPTIONS:
            page_size = PAGE_SIZE_DEFAULT
    except (TypeError, ValueError):
        page_size = PAGE_SIZE_DEFAULT

    # Ordering + Pagination
    qs = qs.order_by("route__route", "index", "code")
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)
    sn_start = page_obj.start_index() - 1

    # Preserve filters across pagination robustly (strip only 'page')
    qd = request.GET.copy()
    qd.pop("page", None)
    filters_qs = qd.urlencode()

    context = {
        "segments": page_obj.object_list,
        "page_obj": page_obj,
        "sn_start": sn_start,

        "routes": routes,
        "states": list(states),
        "selected_route": selected_route,
        "selected_state": selected_state,
        "show_all": show_all,

        "total_length": total_length,
        "total_segments": total_segments,
        "counts": counts,
        "filters_qs": filters_qs,

        # Page-size controls for the template
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,

        # NEW: segment filter (populated + preserved; currently no-op)
        "segments_for_filter": segments_for_filter,
        "selected_segment": selected_segment,
    }
    return render(request, "website/road_analysis.html", context)

# ----------------- Helpers and upload pipeline below (unchanged) -----------------

def _in_lat_range(val):
    return Decimal("-90") <= val <= Decimal("90")

def _in_lon_range(val):
    return Decimal("-180") <= val <= Decimal("180")

def _parse_int_or_zero(s):
    try:
        return int(str(s).strip())
    except Exception:
        return 0

def _prime_route_max_index():
    """
    Build a dict: { route_id: current_max_index_int } by casting Segment.index (CharField) to int.
    Non-numeric or blank indexes are treated as 0.
    """
    route_max = defaultdict(int)
    from all_roads.models import Segment  # local import to avoid circulars on module import
    qs = Segment.objects.values("route_id", "index")
    for row in qs:
        route_max[row["route_id"]] = max(route_max[row["route_id"]], _parse_int_or_zero(row["index"]))
    return route_max

def _next_index_for_route(route_obj, cache):
    """
    Return the next two-digit index string per route (01, 02, … 99).
    Uses and updates a mutable cache dict keyed by route_id.
    """
    rid = route_obj.id
    current = cache.get(rid, 0)
    nxt = current + 1
    cache[rid] = nxt
    # zero-pad to length 2 (your model has max_length=2)
    return str(nxt).zfill(2)

try:
    import openpyxl   # for .xlsx
except Exception:
    openpyxl = None

try:
    import xlrd       # for .xls
except Exception:
    xlrd = None

def _road_code_from_route(route_code: str) -> str:
    s = (route_code or "").strip().upper()
    if not s:
        return "F"
    if s[0] == "F":
        return "F"
    if s[0] in ("A", "E"):
        return "A"
    return "F"

REQUIRED_HEADERS = [
    "ROUTE", "SEGMENT CODE", "STATE", "SEGMENT NAME",
    "START_LAT", "START_LON", "END_LAT", "END_LON"
]

def _to_decimal(s, field_name, rownum, errors):
    try:
        if s is None or s == "":
            return Decimal("0")
        return Decimal(str(s).strip())
    except (InvalidOperation, ValueError):
        errors.append(f"Row {rownum}: invalid decimal for {field_name} = {s!r}")
        return Decimal("0")

def _normalize_headers(headers):
    norm = []
    for h in headers:
        h = (h or "").strip().upper().replace("_", " ")
        norm.append(h)
    return norm

def _is_blank_row(cells):
    if not cells:
        return True
    for c in cells:
        if c is None:
            continue
        if isinstance(c, (int, float)):
            return False
        if str(c).strip() != "":
            return False
    return True

def _read_rows(fileobj, filename):
    """
    Yield dicts keyed by REQUIRED_HEADERS from CSV/XLSX/XLS.
    """
    name = filename.lower()
    if name.endswith(".csv"):
        data = fileobj.read().decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(data))
        rows = list(reader)
        if not rows:
            return [], ["Empty CSV"]
        headers = _normalize_headers(rows[0])
        required_norm = _normalize_headers(REQUIRED_HEADERS)
        norm_to_canon = dict(zip(required_norm, REQUIRED_HEADERS))

        idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        missing = [norm_to_canon[h] for h in required_norm if h not in headers]
        if missing:
            return [], [f"Missing headers: {', '.join(missing)}"]

        out = []
        for i, r in enumerate(rows[1:], start=2):
            if _is_blank_row(r):
                continue
            def cell(h):
                j = idx[h]
                return r[j] if j < len(r) else ""
            out.append({
                "ROUTE": cell("ROUTE"),
                "SEGMENT CODE": cell("SEGMENT CODE"),
                "STATE": cell("STATE"),
                "SEGMENT NAME": cell("SEGMENT NAME"),
                "START_LAT": cell("START_LAT"),
                "START_LON": cell("START_LON"),
                "END_LAT": cell("END_LAT"),
                "END_LON": cell("END_LON"),
                "_rownum": i,
            })
        return out, []

    elif name.endswith(".xlsx"):
        if openpyxl is None:
            return [], ["openpyxl not installed (required for .xlsx)"]
        wb = openpyxl.load_workbook(fileobj, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return [], ["Empty XLSX"]
        headers = _normalize_headers(rows[0])
        required_norm = _normalize_headers(REQUIRED_HEADERS)
        norm_to_canon = dict(zip(required_norm, REQUIRED_HEADERS))

        idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        missing = [norm_to_canon[h] for h in required_norm if h not in headers]
        if missing:
            return [], [f"Missing headers: {', '.join(missing)}"]

        out = []
        for i, r in enumerate(rows[1:], start=2):
            def cell(h):
                j = idx[h]
                return r[j] if j < len(r or []) else ""
            out.append({
                "ROUTE": cell("ROUTE"),
                "SEGMENT CODE": cell("SEGMENT CODE"),
                "STATE": cell("STATE"),
                "SEGMENT NAME": cell("SEGMENT NAME"),
                "START_LAT": cell("START_LAT"),
                "START_LON": cell("START_LON"),
                "END_LAT": cell("END_LAT"),
                "END_LON": cell("END_LON"),
                "_rownum": i,
            })
        return out, []

    elif name.endswith(".xls"):
        if xlrd is None:
            return [], ["xlrd not installed (required for .xls)"]
        book = xlrd.open_workbook(file_contents=fileobj.read())
        sheet = book.sheet_by_index(0)
        # NOTE: If you plan to support .xls soon, ensure you read headers from the sheet:
        # headers = _normalize_headers(sheet.row_values(0))
        # required_norm = _normalize_headers(REQUIRED_HEADERS)
        # norm_to_canon = dict(zip(required_norm, REQUIRED_HEADERS))
        # idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        # ... (left as-is per original structure)

        # Minimal compatibility (assuming order matches REQUIRED_HEADERS):
        out = []
        for i in range(1, sheet.nrows):
            r = sheet.row_values(i)
            out.append({
                "ROUTE": r[0] if len(r) > 0 else "",
                "SEGMENT CODE": r[1] if len(r) > 1 else "",
                "STATE": r[2] if len(r) > 2 else "",
                "SEGMENT NAME": r[3] if len(r) > 3 else "",
                "START_LAT": r[4] if len(r) > 4 else "",
                "START_LON": r[5] if len(r) > 5 else "",
                "END_LAT": r[6] if len(r) > 6 else "",
                "END_LON": r[7] if len(r) > 7 else "",
                "_rownum": i + 1,
            })
        return out, []
    else:
        return [], [f"Unsupported file type: {filename}"]

def uploads(request):
    result = None
    if request.method == "POST":
        form = UploadSegmentsForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["segment_file"]
            auto_index = form.cleaned_data.get("auto_index", False)

            rows, header_errors = _read_rows(f, f.name)
            if header_errors:
                result = {"created": 0, "updated": 0, "skipped": 0, "errors": header_errors}
            else:
                created = updated = skipped = 0
                errors = []

                # Index cache primed once for the whole file
                route_index_cache = _prime_route_max_index() if auto_index else {}

                with transaction.atomic():
                    for row in rows:
                        route_code = str(row["ROUTE"] or "").strip().upper()
                        seg_code   = str(row["SEGMENT CODE"] or "").strip().upper()
                        state      = str(row["STATE"] or "").strip()
                        name       = str(row["SEGMENT NAME"] or "").strip()
                        rnum       = row.get("_rownum", "?")

                        if not route_code or not seg_code:
                            skipped += 1
                            errors.append(f"Row {rnum}: missing ROUTE or SEGMENT CODE.")
                            continue

                        # Convert to Decimal
                        start_lat = _to_decimal(row["START_LAT"], "START_LAT", rnum, errors)
                        start_lon = _to_decimal(row["START_LON"], "START_LON", rnum, errors)
                        end_lat   = _to_decimal(row["END_LAT"], "END_LAT", rnum, errors)
                        end_lon   = _to_decimal(row["END_LON"], "END_LON", rnum, errors)

                        # Enforce coordinate ranges
                        coord_bad = False
                        if not _in_lat_range(start_lat):
                            errors.append(f"Row {rnum}: START_LAT out of range [-90, 90].")
                            coord_bad = True
                        if not _in_lon_range(start_lon):
                            errors.append(f"Row {rnum}: START_LON out of range [-180, 180].")
                            coord_bad = True
                        if not _in_lat_range(end_lat):
                            errors.append(f"Row {rnum}: END_LAT out of range [-90, 90].")
                            coord_bad = True
                        if not _in_lon_range(end_lon):
                            errors.append(f"Row {rnum}: END_LON out of range [-180, 180].")
                            coord_bad = True

                        if coord_bad:
                            skipped += 1
                            continue
                        
                        # Ensure Road/Route mapping (F* -> 'F'; A*/E* -> 'A')
                        road_code = _road_code_from_route(route_code)
                        road_obj, _ = Road.objects.get_or_create(road=road_code)

                        route_obj, created_route = Route.objects.get_or_create(
                            route=route_code,
                            defaults={"road": road_obj, "index": ""},
                        )

                        if not created_route and route_obj.road_id != road_obj.id:
                            route_obj.road = road_obj
                            route_obj.save(update_fields=["road"])

                        defaults = {
                            "route": route_obj,
                            "name": name,
                            "state": state,
                            "start_lat": start_lat,
                            "start_lon": start_lon,
                            "end_lat": end_lat,
                            "end_lon": end_lon,
                            "error_processing": False,
                        }

                        obj, was_created = Segment.objects.update_or_create(
                            code=seg_code,
                            defaults=defaults,
                        )

                        if was_created:
                            if auto_index and not obj.index:
                                obj.index = _next_index_for_route(route_obj, route_index_cache)
                                obj.save(update_fields=["index"])
                            created += 1
                        else:
                            updated += 1

                result = {"created": created, "updated": updated, "skipped": skipped, "errors": errors}
        else:
            result = {"created": 0, "updated": 0, "skipped": 0, "errors": ["Invalid form submission."]}
    else:
        form = UploadSegmentsForm()

    return render(request, "website/uploads.html", {"form": form, "result": result})

def segment_code_search(request):
    """
    Return top matching segment codes for typeahead.
    GET /segments/search/?q=AB -> { "results": ["AB01", "AB02", ...] }
    """
    q = (request.GET.get("q") or "").strip()
    qs = Segment.objects.order_by("code")
    if q:
        qs = qs.filter(code__icontains=q)
    codes = list(qs.values_list("code", flat=True).distinct()[:20])  # cap results
    return JsonResponse({"results": codes})