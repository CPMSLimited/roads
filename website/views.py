from django.shortcuts import render
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, Count, Q
from django.db import transaction
from all_roads.models import Segment, Route
from urllib.parse import urlencode
from django.core.paginator import Paginator
import csv
import io
from .forms import UploadSegmentsForm
from all_roads.models import Segment, Route, Road
from collections import defaultdict
from django.db.models import Max
from django.db.models.functions import Cast
from django.db.models import IntegerField

STATUS_BUCKETS = {
    "good": {"codes": ["339933", "006600"]},         # Good (>=90 km/h)
    "tolerable": {"codes": ["00CC00", "FFFFCC"]},    # OK / Manageable
    "intolerable": {"codes": ["FF9966", "FF5050"]},  # Poor / Bad
    "failed": {"codes": ["FF0000", "666699"]},       # Werser / No response
}

def landing(request):
    return render(request, "website/landing.html")

def road_analysis(request):
    return render(request, "website/road_analysis.html")

def uploads(request):
    if request.method == "POST":
        # Placeholder only — real behaviour to be added when you share details
        # uploaded_file = request.FILES.get("segment_file")
        return HttpResponse("Upload received (stub). Behaviour to be defined.")
    return render(request, "website/uploads.html")

def road_analysis(request):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()

    # Read query params
    selected_route = request.GET.get("route") or ""
    selected_state = request.GET.get("state") or ""
    show_all = request.GET.get("show") == "all"

    # Enforce single active filter on server side as well (defensive)
    if show_all:
        selected_route = ""
        selected_state = ""
    elif selected_route:
        selected_state = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_route = ""
        qs = qs.filter(state=selected_state)

    # Aggregates
    agg = qs.aggregate(total_length=Sum("distance"), total_segments=Count("id"))
    total_length = (agg["total_length"] or Decimal("0.00")).quantize(Decimal("0.01"))
    total_segments = agg["total_segments"] or 0

    counts = {k: qs.filter(status__in=v["codes"]).count() for k, v in STATUS_BUCKETS.items()}

    # Options for selects
    routes = Route.objects.only("route").order_by("route")
    states = (
        Segment.objects.exclude(state="")
        .order_by("state")
        .values_list("state", flat=True)
        .distinct()
    )

    # Pagination (50 per page)
    qs = qs.order_by("route__route", "index", "code")
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    sn_start = page_obj.start_index() - 1

    # Build querystring for pagination with the single active filter
    filters = {}
    if selected_route:
        filters["route"] = selected_route
    elif selected_state:
        filters["state"] = selected_state
    elif show_all:
        filters["show"] = "all"
    filters_qs = urlencode(filters)

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
    }
    return render(request, "website/road_analysis.html", context)

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
    # Cast may fail on non-numeric text; safer approach is to pull values and parse in Python:
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
        return "F"  # or return None and treat as error upstream
    if s[0] == "F":
        return "F"
    if s[0] in ("A", "E"):
        return "A"
    return "F"  # fallback; change to raising an error if you want to be strict

REQUIRED_HEADERS = [
    "ROUTE", "SEGMENT CODE", "STATE", "SEGMENT NAME",
    "START_LAT", "START_LON", "END_LAT", "END_LON"
]

def _to_decimal(s, field_name, rownum, errors):
    try:
        if s is None or s == "":
            return Decimal("0")
        # Accept strings/numbers, strip spaces
        return Decimal(str(s).strip())
    except (InvalidOperation, ValueError):
        errors.append(f"Row {rownum}: invalid decimal for {field_name} = {s!r}")
        return Decimal("0")


def _normalize_headers(headers):
    """
    Make header matching robust:
    - strip spaces
    - upper-case
    - allow underscores vs spaces interchangeably
    """
    norm = []
    for h in headers:
        h = (h or "").strip().upper().replace("_", " ")
        norm.append(h)
    return norm

def _is_blank_row(cells):
    """
    Return True if a row is effectively empty: all cells are None/''/whitespace.
    Accepts a list/tuple of cell values from CSV/XLSX/XLS.
    """
    if not cells:
        return True
    for c in cells:
        if c is None:
            continue
        # numbers (0.0) count as content; only whitespace is blank
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
        headers = _normalize_headers(rows[0])  # sheet headers → upper + spaces
        required_norm = _normalize_headers(REQUIRED_HEADERS)  # required list → same normalisation
        # map back from normalised name to the original canonical key we'll use later
        norm_to_canon = dict(zip(required_norm, REQUIRED_HEADERS))

        idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        missing = [norm_to_canon[h] for h in required_norm if h not in headers]
        if missing:
            return [], [f"Missing headers: {', '.join(missing)}"]

        out = []
        for i, r in enumerate(rows[1:], start=2):
            if _is_blank_row(r):
                continue  # silently ignore empty/trailing rows

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
        headers = _normalize_headers(rows[0])  # sheet headers → upper + spaces
        required_norm = _normalize_headers(REQUIRED_HEADERS)  # required list → same normalisation
        # map back from normalised name to the original canonical key we'll use later
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
        headers = _normalize_headers(rows[0])  # sheet headers → upper + spaces
        required_norm = _normalize_headers(REQUIRED_HEADERS)  # required list → same normalisation
        # map back from normalised name to the original canonical key we'll use later
        norm_to_canon = dict(zip(required_norm, REQUIRED_HEADERS))

        idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        missing = [norm_to_canon[h] for h in required_norm if h not in headers]
        if missing:
            return [], [f"Missing headers: {', '.join(missing)}"]

        out = []
        for i in range(1, sheet.nrows):
            r = sheet.row_values(i)
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

                # Index cache primed once for the whole file (fast even for 500–700 rows)
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
                        
                        # Ensure Road and Route obey the rule (F* -> Road 'F'; A*/E* -> Road 'A')
                        road_code = _road_code_from_route(route_code)
                        road_obj, _ = Road.objects.get_or_create(road=road_code)

                        route_obj, created_route = Route.objects.get_or_create(
                            route=route_code,
                            defaults={"road": road_obj, "index": ""},
                        )

                        # If the route already existed but points to a different Road, fix it
                        if not created_route and route_obj.road_id != road_obj.id:
                            route_obj.road = road_obj
                            route_obj.save(update_fields=["road"])


                        # Determine index value:
                        #   - If the Segment exists, keep its existing index
                        #   - If creating and auto_index is on, auto-assign next index for the route
                        #   - Else leave blank (or set from a CSV column if you later add one)
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

                        # Upsert by unique code
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
                            # If updating, leave index as-is to avoid reshuffling existing order
                            updated += 1

                result = {"created": created, "updated": updated, "skipped": skipped, "errors": errors}
        else:
            result = {"created": 0, "updated": 0, "skipped": 0, "errors": ["Invalid form submission."]}
    else:
        form = UploadSegmentsForm()

    return render(request, "website/uploads.html", {"form": form, "result": result})