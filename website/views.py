from django.shortcuts import render
from django.http import HttpResponse
from decimal import Decimal
from django.db.models import Sum, Count, Q
from all_roads.models import Segment, Route
from urllib.parse import urlencode
from django.core.paginator import Paginator

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

# def road_analysis(request):
#     qs = Segment.objects.select_related("route", "start_point", "end_point").all()

#     # ── Filters from querystring
#     selected_route = request.GET.get("route") or ""
#     selected_state = request.GET.get("state") or ""
#     show_all = request.GET.get("show") == "all"

#     if not show_all:
#         if selected_route:
#             qs = qs.filter(route__route=selected_route)
#         if selected_state:
#             qs = qs.filter(state=selected_state)

#     # ── Aggregates for metrics
#     agg = qs.aggregate(total_length=Sum("distance"), total_segments=Count("id"))
#     total_length = (agg["total_length"] or Decimal("0.00")).quantize(Decimal("0.01"))
#     total_segments = agg["total_segments"] or 0

#     counts = {}
#     for bucket, meta in STATUS_BUCKETS.items():
#         counts[bucket] = qs.filter(status__in=meta["codes"]).count()

#     # ── Options for selects
#     routes = Route.objects.only("route").order_by("route")
#     states = (
#         Segment.objects.exclude(state="")
#         .order_by("state")
#         .values_list("state", flat=True)
#         .distinct()
#     )

#     # ── Pagination (50 per page)
#     qs = qs.order_by("route__route", "index", "code")
#     paginator = Paginator(qs, 50)
#     page_number = request.GET.get("page")
#     page_obj = paginator.get_page(page_number)

#     # For SN column numbering in template
#     sn_start = page_obj.start_index() - 1

#     # Keep filters in pagination links
#     filters = {}
#     if selected_route:
#         filters["route"] = selected_route
#     if selected_state:
#         filters["state"] = selected_state
#     if show_all:
#         filters["show"] = "all"
#     filters_qs = urlencode(filters)

#     context = {
#         "page_obj": page_obj,
#         "segments": page_obj.object_list,
#         "routes": routes,
#         "states": list(states),
#         "selected_route": "" if show_all else selected_route,
#         "selected_state": "" if show_all else selected_state,
#         "show_all": show_all,
#         "filters_qs": filters_qs,
#         "sn_start": sn_start,
#         "total_length": total_length,
#         "total_segments": total_segments,
#         "counts": counts,
#     }
#     return render(request, "website/road_analysis.html", context)


# website/views.py
# from decimal import Decimal
# from urllib.parse import urlencode
# from django.core.paginator import Paginator
# from django.db.models import Sum, Count
# from django.shortcuts import render
# from all_roads.models import Segment, Route

# STATUS_BUCKETS = {
#     "good": {"codes": ["339933", "006600"]},
#     "tolerable": {"codes": ["00CC00", "FFFFCC"]},
#     "intolerable": {"codes": ["FF9966", "FF5050"]},
#     "failed": {"codes": ["FF0000", "666699"]},
# }

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

