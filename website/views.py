# website/views.py

import logging

from all_roads.models import (
    Segment,
    Route,
    Road,
    State,
    SubSegment,
    DefectType,
    RootCauseAnalysis,
    RootCauseDetail,
    PhysicalInspection,
    PhysicalInspectionAnalysis,
    PhysicalInspectionCharacteristic,
    PhysicalInspectionAttachment,
)
from all_roads.services import refresh_segment_and_subsegments
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Sum, Count, Q, IntegerField, Max
from django.db.models.functions import Cast, Trim, Upper
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import UploadSegmentsForm, UploadSubSegmentsForm
import csv
import io

logger = logging.getLogger(__name__)

# ---- Status buckets used for counts/mini-chart (hex codes) ----
STATUS_BUCKETS = {
    "good": {"codes": ["339933", "006600"]},         # Good (>=90 km/h)
    "tolerable": {"codes": ["00CC00", "FFFFCC"]},    # OK / Manageable
    "intolerable": {"codes": ["FF9966", "FF5050"]},  # Poor / Bad
    "failed": {"codes": ["FF0000"]},                 # Failed
    "no_response": {"codes": ["666699"]},            # Unknown / no response
}

# ---- Pagination options (Point 5) ----
PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_OPTIONS = [25, 50, 100]

def landing(request):
    return render(request, "website/landing.html", {"active_page": "home"})


def _overview_metrics(qs):
    agg = qs.aggregate(total_length=Sum("distance"), total_segments=Count("id"))
    return {
        "total_length": (agg["total_length"] or Decimal("0.00")).quantize(Decimal("0.01")),
        "total_segments": agg["total_segments"] or 0,
        "counts": {k: qs.filter(status__in=v["codes"]).count() for k, v in STATUS_BUCKETS.items()},
    }


def _build_inventory_context(request, active_page="inventory"):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()
    current_view = request.GET.get("view") or "map"
    selected_road = request.GET.get("road") or ""
    selected_route = request.GET.get("route") or ""
    selected_state = (request.GET.get("state") or "").strip()

    # Keep one active filter at a time.
    if selected_road:
        selected_route = ""
        selected_state = ""
        qs = qs.filter(route__road__road=selected_road)
    elif selected_route:
        selected_road = ""
        selected_state = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_road = ""
        selected_route = ""
        qs = qs.filter(state__iexact=selected_state)

    roads = Road.objects.only("road").order_by("road")
    routes = Route.objects.only("route").order_by("route")
    states = State.objects.only("state").order_by("state").values_list("state", flat=True)

    paginator = Paginator(qs.order_by("route__route", "index", "code"), 50)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    filters = {}
    if current_view:
        filters["view"] = current_view
    if selected_road:
        filters["road"] = selected_road
    if selected_route:
        filters["route"] = selected_route
    if selected_state:
        filters["state"] = selected_state

    metrics = _overview_metrics(qs)
    all_rows = list(qs.order_by("route__route", "code")[:12])
    focus_segment = all_rows[0] if all_rows else None
    unique_route_count = qs.values("route_id").distinct().count()

    return {
        "active_page": active_page,
        "segments": page_obj.object_list,
        "page_obj": page_obj,
        "roads": roads,
        "routes": routes,
        "states": list(states),
        "selected_road": selected_road,
        "selected_route": selected_route,
        "selected_state": selected_state,
        "current_view": current_view,
        "filters_qs": urlencode(filters),
        "number_routes": unique_route_count,
        "segment_length_total": "----",
        "focus_segment": focus_segment,
        "report_rows": all_rows[:3],
        **metrics,
    }


def road_inventory(request):
    context = _build_inventory_context(request, active_page="inventory")
    return render(request, "website/road_inventory.html", context)


def _build_motorability_and_condition_context(request):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()
    current_view = request.GET.get("view") or "map"
    selected_road = request.GET.get("road") or ""
    selected_route = request.GET.get("route") or ""
    selected_state = (request.GET.get("state") or "").strip()
    selected_speed = (request.GET.get("speed") or "").strip().lower()

    # Keep one active filter at a time.
    if selected_road:
        selected_route = ""
        selected_state = ""
        selected_speed = ""
        qs = qs.filter(route__road__road=selected_road)
    elif selected_route:
        selected_road = ""
        selected_state = ""
        selected_speed = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_road = ""
        selected_route = ""
        selected_speed = ""
        qs = qs.filter(state__iexact=selected_state)
    elif selected_speed in STATUS_BUCKETS:
        selected_road = ""
        selected_route = ""
        selected_state = ""
        qs = qs.filter(status__in=STATUS_BUCKETS[selected_speed]["codes"])

    roads = Road.objects.only("road").order_by("road")
    routes = Route.objects.only("route").order_by("route")
    states = State.objects.only("state").order_by("state").values_list("state", flat=True)
    speed_options = [
        ("good", "Good"),
        ("tolerable", "Tolerable"),
        ("intolerable", "Intolerable"),
        ("failed", "Failed"),
        ("no_response", "No response"),
    ]

    paginator = Paginator(qs.order_by("route__route", "index", "code"), 50)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    filters = {}
    if current_view:
        filters["view"] = current_view
    if selected_road:
        filters["road"] = selected_road
    if selected_route:
        filters["route"] = selected_route
    if selected_state:
        filters["state"] = selected_state
    if selected_speed:
        filters["speed"] = selected_speed

    metrics = _overview_metrics(qs)
    all_rows = list(qs.order_by("route__route", "code")[:12])
    focus_segment = all_rows[0] if all_rows else None
    unique_route_count = qs.values("route_id").distinct().count()

    return {
        "active_page": "motorability_and_condition",
        "segments": page_obj.object_list,
        "page_obj": page_obj,
        "roads": roads,
        "routes": routes,
        "states": list(states),
        "speed_options": speed_options,
        "selected_road": selected_road,
        "selected_route": selected_route,
        "selected_state": selected_state,
        "selected_speed": selected_speed,
        "current_view": current_view,
        "filters_qs": urlencode(filters),
        "number_routes": unique_route_count,
        "segment_length_total": "----",
        "focus_segment": focus_segment,
        "report_rows": all_rows[:3],
        **metrics,
    }


def motorability_and_condition(request):
    context = _build_motorability_and_condition_context(request)
    return render(request, "website/motorability_and_condition.html", context)

def _filtered_segments_for_road_motorability(request):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()
    current_view = request.GET.get("view") or "map"
    selected_road = request.GET.get("road") or ""
    selected_route = request.GET.get("route") or ""
    selected_state = (request.GET.get("state") or "").strip()
    selected_speed = (request.GET.get("speed") or "").strip().lower()

    if selected_road:
        selected_route = ""
        selected_state = ""
        selected_speed = ""
        qs = qs.filter(route__road__road=selected_road)
    elif selected_route:
        selected_road = ""
        selected_state = ""
        selected_speed = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_road = ""
        selected_route = ""
        selected_speed = ""
        qs = qs.filter(state__iexact=selected_state)
    elif selected_speed in STATUS_BUCKETS:
        selected_road = ""
        selected_route = ""
        selected_state = ""
        qs = qs.filter(status__in=STATUS_BUCKETS[selected_speed]["codes"])

    return {
        "qs": qs,
        "current_view": current_view,
        "selected_road": selected_road,
        "selected_route": selected_route,
        "selected_state": selected_state,
        "selected_speed": selected_speed,
    }


def _build_road_motorability_context(request):
    filtered = _filtered_segments_for_road_motorability(request)
    qs = filtered["qs"]
    roads = Road.objects.only("road").order_by("road")
    routes = Route.objects.only("route").order_by("route")
    states = State.objects.only("state").order_by("state").values_list("state", flat=True)
    speed_options = [
        ("good", "Good"),
        ("tolerable", "Tolerable"),
        ("intolerable", "Intolerable"),
        ("failed", "Failed"),
        ("no_response", "No response"),
    ]

    paginator = Paginator(qs.order_by("route__route", "index", "code"), 50)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    filters = {}
    if filtered["current_view"]:
        filters["view"] = filtered["current_view"]
    if filtered["selected_road"]:
        filters["road"] = filtered["selected_road"]
    if filtered["selected_route"]:
        filters["route"] = filtered["selected_route"]
    if filtered["selected_state"]:
        filters["state"] = filtered["selected_state"]
    if filtered["selected_speed"]:
        filters["speed"] = filtered["selected_speed"]

    metrics = _overview_metrics(qs)
    all_rows = list(qs.order_by("route__route", "code")[:12])
    focus_segment = all_rows[0] if all_rows else None
    unique_route_count = qs.values("route_id").distinct().count()

    return {
        "active_page": "road_motorability",
        "segments": page_obj.object_list,
        "page_obj": page_obj,
        "roads": roads,
        "routes": routes,
        "states": list(states),
        "speed_options": speed_options,
        "selected_road": filtered["selected_road"],
        "selected_route": filtered["selected_route"],
        "selected_state": filtered["selected_state"],
        "selected_speed": filtered["selected_speed"],
        "current_view": filtered["current_view"],
        "filters_qs": urlencode(filters),
        "number_routes": unique_route_count,
        "segment_length_total": "----",
        "focus_segment": focus_segment,
        "report_rows": all_rows[:3],
        **metrics,
    }


def road_motorability(request):
    context = _build_road_motorability_context(request)
    return render(request, "website/road_motorability.html", context)


def road_motorability_map_data(request):
    filtered = _filtered_segments_for_road_motorability(request)
    segments = filtered["qs"].order_by("route__route", "index", "code")
    features = []

    for seg in segments:
        try:
            start_lat = float(seg.start_lat)
            start_lon = float(seg.start_lon)
            end_lat = float(seg.end_lat)
            end_lon = float(seg.end_lon)
        except (TypeError, ValueError, InvalidOperation):
            continue

        if start_lat == end_lat and start_lon == end_lon:
            geometry = {"type": "Point", "coordinates": [start_lon, start_lat]}
        else:
            geometry = {
                "type": "LineString",
                "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
            }

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "code": seg.code,
                    "route": getattr(seg.route, "route", ""),
                    "state": seg.state or "",
                    "distance": float(seg.distance or 0),
                    "avg_speed": float(seg.avg_speed or 0),
                    "status": seg.status or "666699",
                },
            }
        )

    return JsonResponse({"type": "FeatureCollection", "features": features})


def library(request):
    mode_value = request.GET.get("mode")
    if mode_value == "form":
        library_mode = "form"
    elif mode_value == "view":
        library_mode = "view"
    else:
        library_mode = "summary"
    analysis_id = request.GET.get("analysis") or request.POST.get("analysis_id")
    subsegment_id = request.GET.get("subsegment") or request.POST.get("subsegment_id")
    subsegments_qs = SubSegment.objects.select_related("segment").order_by("segment_id", "position")
    selected_subsegment = None
    if subsegment_id:
        selected_subsegment = subsegments_qs.filter(pk=subsegment_id).first()
    if selected_subsegment is None:
        selected_subsegment = subsegments_qs.first()
    defect_type_qs = DefectType.objects.filter(is_active=True).order_by("label")
    description_options = list(defect_type_qs.values_list("code", "label"))
    if not description_options:
        description_options = list(RootCauseAnalysis.DESCRIPTION_CHOICES)
    existing_analysis = None
    if analysis_id:
        existing_analysis = RootCauseAnalysis.objects.prefetch_related("defect_types").filter(pk=analysis_id).first()
        if existing_analysis and selected_subsegment is None:
            selected_subsegment = existing_analysis.subsegment

    rca_values = {
        "description": request.POST.get("description", ""),
        "subgrade_properties": request.POST.get("subgrade_properties", ""),
        "vegetation": request.POST.get("vegetation", ""),
        "topography": request.POST.get("topography", ""),
        "drainage_characteristics": request.POST.get("drainage_characteristics", ""),
        "temp_humidity": request.POST.get("temp_humidity", ""),
        "location": request.POST.get("location", ""),
    }
    selected_descriptions = request.POST.getlist("description_options")
    rca_error = ""
    rca_success = request.GET.get("saved") == "1"
    if request.method != "POST" and library_mode == "form" and existing_analysis:
        selected_subsegment = existing_analysis.subsegment
        selected_descriptions = list(existing_analysis.defect_types.values_list("code", flat=True))
        if not selected_descriptions:
            selected_descriptions = existing_analysis.description_options or []
        if not selected_descriptions and existing_analysis.description:
            selected_descriptions = [existing_analysis.description]
        rca_values["location"] = existing_analysis.location
        detail = getattr(existing_analysis, "root_cause_detail", None)
        if detail:
            if detail.natural_feature == RootCauseDetail.FEATURE_SUBGRADE_PROPERTIES:
                rca_values["subgrade_properties"] = detail.characteristic
            elif detail.natural_feature == RootCauseDetail.FEATURE_VEGETATION:
                rca_values["vegetation"] = detail.characteristic
            elif detail.natural_feature == RootCauseDetail.FEATURE_TOPOGRAPHY:
                rca_values["topography"] = detail.characteristic
            elif detail.natural_feature == RootCauseDetail.FEATURE_DRAINAGE_CHARACTERISTICS:
                rca_values["drainage_characteristics"] = detail.characteristic
            elif detail.natural_feature == RootCauseDetail.FEATURE_TEMPERATURE_HUMIDITY:
                rca_values["temp_humidity"] = detail.characteristic

    if request.method == "POST" and library_mode == "form":
        submit_action = request.POST.get("submit_action")
        if submit_action == "complete":
            status_value = RootCauseAnalysis.STATUS_COMPLETE
        else:
            status_value = RootCauseAnalysis.STATUS_DRAFT
        supporting_file = request.FILES.get("supporting_file")

        if selected_subsegment is None:
            rca_error = "No subsegment is available. Add subsegment data before creating root cause analysis."
        elif not selected_descriptions:
            rca_error = "Select at least one defect description."
        else:
            valid_description_values = {value for value, _ in description_options}
            invalid_descriptions = [value for value in selected_descriptions if value not in valid_description_values]
            if invalid_descriptions:
                rca_error = "One or more selected defect descriptions are invalid."
                selected_primary_description = ""
            else:
                selected_primary_description = selected_descriptions[0]

            feature_pairs = [
                (RootCauseDetail.FEATURE_SUBGRADE_PROPERTIES, rca_values["subgrade_properties"]),
                (RootCauseDetail.FEATURE_VEGETATION, rca_values["vegetation"]),
                (RootCauseDetail.FEATURE_TOPOGRAPHY, rca_values["topography"]),
                (RootCauseDetail.FEATURE_DRAINAGE_CHARACTERISTICS, rca_values["drainage_characteristics"]),
                (RootCauseDetail.FEATURE_TEMPERATURE_HUMIDITY, rca_values["temp_humidity"]),
            ]
            selected_feature_pairs = [(feature, value) for feature, value in feature_pairs if value]
            valid_by_feature = {
                feature: {value for value, _ in choices}
                for feature, choices in RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE.items()
            }
            if len(selected_feature_pairs) > 1 and not rca_error:
                rca_error = "Select only one root cause description option."
            invalid_choice = any(
                value not in valid_by_feature.get(feature, set())
                for feature, value in selected_feature_pairs
            )
            if invalid_choice and not rca_error:
                rca_error = "One or more selected characteristic values are invalid."
            if not rca_error:
                with transaction.atomic():
                    location_value = (
                        (rca_values["location"] or "").strip()
                        or (selected_subsegment.code or "")[:32]
                        or "Unknown"
                    )
                    if existing_analysis:
                        analysis = existing_analysis
                        analysis.subsegment = selected_subsegment
                        analysis.location = location_value[:32]
                        analysis.description = selected_primary_description
                        analysis.description_options = selected_descriptions
                        analysis.status = status_value
                        if supporting_file:
                            analysis.supporting_file = supporting_file
                        analysis.save()
                    else:
                        analysis = RootCauseAnalysis.objects.create(
                            subsegment=selected_subsegment,
                            location=location_value[:32],
                            description=selected_primary_description,
                            description_options=selected_descriptions,
                            status=status_value,
                            supporting_file=supporting_file,
                        )
                    selected_defect_types = list(
                        defect_type_qs.filter(code__in=selected_descriptions)
                    )
                    analysis.defect_types.set(selected_defect_types)
                    if selected_feature_pairs:
                        feature, value = selected_feature_pairs[0]
                        RootCauseDetail.objects.update_or_create(
                            root_cause_analysis=analysis,
                            defaults={
                                "natural_feature": feature,
                                "characteristic": value,
                                "root_cause_analysis_text": "",
                            },
                        )
                    elif existing_analysis:
                        RootCauseDetail.objects.filter(root_cause_analysis=analysis).delete()

                return redirect(
                    f"{reverse('library')}?mode=form&saved=1&subsegment={selected_subsegment.pk}&analysis={analysis.pk}"
                )

    root_cause_analyses = (
        RootCauseAnalysis.objects.select_related("subsegment", "subsegment__segment", "root_cause_detail")
        .prefetch_related("defect_types")
        .order_by("-id")
    )
    root_cause_total = root_cause_analyses.count()
    root_cause_draft_count = root_cause_analyses.filter(status=RootCauseAnalysis.STATUS_DRAFT).count()
    root_cause_complete_count = root_cause_analyses.filter(status=RootCauseAnalysis.STATUS_COMPLETE).count()
    description_label_map = dict(description_options)
    draft_rows = []
    complete_rows = []
    for report in root_cause_analyses[:100]:
        selected_values = list(report.defect_types.values_list("code", flat=True))
        if not selected_values:
            selected_values = report.description_options or []
        selected_labels = [description_label_map.get(value) for value in selected_values if value in description_label_map]
        defect_text = ", ".join(label.lower() for label in selected_labels if label) or report.get_description_display()
        condition_label = "Intolerable" if report.pk % 3 == 0 else "Tolerable"
        condition_class = "intolerable" if condition_label == "Intolerable" else "tolerable"
        row = {
            "report": report,
            "defect_text": defect_text,
            "condition_label": condition_label,
            "condition_class": condition_class,
            "engineer_name": "Engineer Ridwan Bankole",
        }
        if report.status == RootCauseAnalysis.STATUS_COMPLETE:
            complete_rows.append(row)
        else:
            draft_rows.append(row)

    for idx, row in enumerate(draft_rows):
        row["date_text"] = "27/12/2025" if idx == 0 else "5 days"
    for idx, row in enumerate(complete_rows):
        row["date_text"] = "2 days" if idx == 0 else "5 days"

    if library_mode == "view" and existing_analysis is None:
        existing_analysis = root_cause_analyses.filter(status=RootCauseAnalysis.STATUS_COMPLETE).first()

    view_defect_text = ""
    view_feature_values = {
        "subgrade_properties": "Not provided",
        "vegetation": "Not provided",
        "topography": "Not provided",
        "drainage_characteristics": "Not provided",
        "temp_humidity": "Not provided",
    }
    supporting_documents = []
    view_segment_status_text = "Unknown"
    view_segment_status_class = "neutral"
    if existing_analysis:
        selected_values = list(existing_analysis.defect_types.values_list("code", flat=True))
        if not selected_values:
            selected_values = existing_analysis.description_options or []
        selected_labels = [description_label_map.get(value) for value in selected_values if value in description_label_map]
        view_defect_text = ", ".join(selected_labels) or existing_analysis.get_description_display()

        detail = getattr(existing_analysis, "root_cause_detail", None)
        if detail:
            characteristic_value = detail.get_characteristic_display()
            feature_key_map = {
                RootCauseDetail.FEATURE_SUBGRADE_PROPERTIES: "subgrade_properties",
                RootCauseDetail.FEATURE_VEGETATION: "vegetation",
                RootCauseDetail.FEATURE_TOPOGRAPHY: "topography",
                RootCauseDetail.FEATURE_DRAINAGE_CHARACTERISTICS: "drainage_characteristics",
                RootCauseDetail.FEATURE_TEMPERATURE_HUMIDITY: "temp_humidity",
            }
            feature_key = feature_key_map.get(detail.natural_feature)
            if feature_key:
                view_feature_values[feature_key] = characteristic_value

        if existing_analysis.supporting_file:
            supporting_documents = [existing_analysis.supporting_file.name.split("/")[-1]]
        else:
            code = existing_analysis.subsegment.code if existing_analysis.subsegment else "A1LAS2-01"
            supporting_documents = [f"{code} Root Cause.jpg", f"{code} Root Cause.jpg"]

        segment_status_code = getattr(getattr(existing_analysis.subsegment, "segment", None), "status", "")
        if segment_status_code in {"FF0000", "FF5050", "FF9966"}:
            view_segment_status_text = "Intolerable"
            view_segment_status_class = "intolerable"
        elif segment_status_code in {"FFFFCC", "00CC00", "339933", "006600"}:
            view_segment_status_text = "Tolerable"
            view_segment_status_class = "tolerable"
        else:
            view_segment_status_text = "No response"
            view_segment_status_class = "neutral"

    return render(
        request,
        "website/library.html",
        {
            "active_page": "library",
            "active_library_tab": "root_cause",
            "library_mode": library_mode,
            "rca_error": rca_error,
            "rca_success": rca_success,
            "subsegments": subsegments_qs[:300],
            "selected_subsegment": selected_subsegment,
            "description_options": description_options,
            "selected_descriptions": selected_descriptions,
            "subgrade_options": RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE[
                RootCauseDetail.FEATURE_SUBGRADE_PROPERTIES
            ],
            "vegetation_options": RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE[
                RootCauseDetail.FEATURE_VEGETATION
            ],
            "topography_options": RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE[
                RootCauseDetail.FEATURE_TOPOGRAPHY
            ],
            "drainage_options": RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE[
                RootCauseDetail.FEATURE_DRAINAGE_CHARACTERISTICS
            ],
            "temperature_humidity_options": RootCauseDetail.CHARACTERISTIC_CHOICES_BY_FEATURE[
                RootCauseDetail.FEATURE_TEMPERATURE_HUMIDITY
            ],
            "rca_values": rca_values,
            "current_analysis": existing_analysis,
            "draft_rows": draft_rows,
            "complete_rows": complete_rows,
            "root_cause_total": root_cause_total,
            "root_cause_draft_count": root_cause_draft_count,
            "root_cause_complete_count": root_cause_complete_count,
            "view_defect_text": view_defect_text,
            "view_feature_values": view_feature_values,
            "supporting_documents": supporting_documents,
            "view_segment_status_text": view_segment_status_text,
            "view_segment_status_class": view_segment_status_class,
        },
    )


def library_overview(request):
    return render(
        request,
        "website/library.html",
        {
            "active_page": "library",
            "active_library_tab": "overview",
        },
    )


def physical_inspection(request):
    mode_value = request.GET.get("mode") or request.POST.get("mode")
    if mode_value == "form":
        library_mode = "form"
    elif mode_value == "view":
        library_mode = "view"
    else:
        library_mode = "summary"
    physical_success = request.GET.get("saved") == "1"
    physical_error = ""
    inspection_id = request.GET.get("inspection") or request.POST.get("inspection_id")
    defect_options = list(
        DefectType.objects.filter(is_active=True).order_by("label").values_list("code", "label")
    )
    if not defect_options:
        defect_options = list(RootCauseAnalysis.DESCRIPTION_CHOICES)

    horizontal_alignment_options = [
        value
        for value in PhysicalInspectionCharacteristic.CHARACTERISTICS_BY_OPTION[
            PhysicalInspectionAnalysis.OPTION_HORIZONTAL_ALIGNMENT
        ]
    ]
    vertical_alignment_options = [
        value
        for value in PhysicalInspectionCharacteristic.CHARACTERISTICS_BY_OPTION[
            PhysicalInspectionAnalysis.OPTION_VERTICAL_ALIGNMENT
        ]
    ]
    bridge_options = [
        value
        for value in PhysicalInspectionCharacteristic.CHARACTERISTICS_BY_OPTION[
            PhysicalInspectionAnalysis.OPTION_BRIDGES
        ]
    ]

    existing_inspection = None
    if inspection_id:
        existing_inspection = (
            PhysicalInspection.objects.select_related("subsegment", "subsegment__segment")
            .prefetch_related("defect_types", "analysis_rows__characteristics")
            .filter(pk=inspection_id)
            .first()
        )

    physical_values = {
        "segment_id": request.POST.get("segment_id", "").strip(),
        "horizontal_alignment": request.POST.get("horizontal_alignment", "").strip(),
        "vertical_alignment": request.POST.get("vertical_alignment", "").strip(),
        "bridges": request.POST.get("bridges", "").strip(),
        "selected_defects": request.POST.getlist("defect_types"),
    }
    if request.method != "POST" and library_mode == "form" and existing_inspection:
        physical_values["segment_id"] = existing_inspection.subsegment.code
        physical_values["selected_defects"] = list(
            existing_inspection.defect_types.values_list("code", flat=True)
        )
        option_rows = {row.option: row for row in existing_inspection.analysis_rows.all()}
        horizontal_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_HORIZONTAL_ALIGNMENT)
        if horizontal_row:
            first = horizontal_row.characteristics.first()
            if first:
                physical_values["horizontal_alignment"] = first.value or first.characteristic
        vertical_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_VERTICAL_ALIGNMENT)
        if vertical_row:
            first = vertical_row.characteristics.first()
            if first:
                physical_values["vertical_alignment"] = first.value or first.characteristic
        bridges_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_BRIDGES)
        if bridges_row:
            first = bridges_row.characteristics.first()
            if first:
                physical_values["bridges"] = first.value or first.characteristic

    if request.method == "POST" and library_mode == "form":
        submit_action = request.POST.get("submit_action")
        status_value = (
            PhysicalInspection.STATUS_COMPLETE
            if submit_action == "complete"
            else PhysicalInspection.STATUS_DRAFT
        )
        subsegment_code = physical_values["segment_id"]
        selected_defects = physical_values["selected_defects"]
        valid_defect_codes = {value for value, _ in defect_options}
        selected_defects = [code for code in selected_defects if code in valid_defect_codes]

        if not subsegment_code:
            physical_error = "Segment id is required."
        else:
            selected_subsegment = SubSegment.objects.filter(code__iexact=subsegment_code).first()
            if selected_subsegment is None:
                physical_error = "Segment id was not found."
            elif not selected_defects:
                physical_error = "Select at least one defect description."
            else:
                valid_horizontal = set(horizontal_alignment_options)
                valid_vertical = set(vertical_alignment_options)
                valid_bridges = set(bridge_options)
                horizontal_value = physical_values["horizontal_alignment"]
                vertical_value = physical_values["vertical_alignment"]
                bridges_value = physical_values["bridges"]
                if horizontal_value and horizontal_value not in valid_horizontal:
                    physical_error = "Invalid horizontal alignment value."
                elif vertical_value and vertical_value not in valid_vertical:
                    physical_error = "Invalid vertical alignment value."
                elif bridges_value and bridges_value not in valid_bridges:
                    physical_error = "Invalid bridges value."

        if not physical_error:
            with transaction.atomic():
                if existing_inspection:
                    inspection = existing_inspection
                    inspection.subsegment = selected_subsegment
                    inspection.status = status_value
                    inspection.save()
                    inspection.analysis_rows.all().delete()
                else:
                    inspection = PhysicalInspection.objects.create(
                        subsegment=selected_subsegment,
                        status=status_value,
                    )
                inspection.defect_types.set(
                    DefectType.objects.filter(code__in=selected_defects, is_active=True)
                )

                if physical_values["horizontal_alignment"]:
                    horizontal_row = PhysicalInspectionAnalysis.objects.create(
                        inspection=inspection,
                        consideration_type=PhysicalInspectionAnalysis.CONSIDERATION_DESIGN,
                        option=PhysicalInspectionAnalysis.OPTION_HORIZONTAL_ALIGNMENT,
                        option_description=(request.POST.get("horizontal_alignment_description", "") or "").strip(),
                    )
                    PhysicalInspectionCharacteristic.objects.create(
                        analysis=horizontal_row,
                        characteristic=physical_values["horizontal_alignment"],
                        value=physical_values["horizontal_alignment"],
                    )

                if physical_values["vertical_alignment"]:
                    vertical_row = PhysicalInspectionAnalysis.objects.create(
                        inspection=inspection,
                        consideration_type=PhysicalInspectionAnalysis.CONSIDERATION_DESIGN,
                        option=PhysicalInspectionAnalysis.OPTION_VERTICAL_ALIGNMENT,
                        option_description=(request.POST.get("vertical_alignment_description", "") or "").strip(),
                    )
                    PhysicalInspectionCharacteristic.objects.create(
                        analysis=vertical_row,
                        characteristic=physical_values["vertical_alignment"],
                        value=physical_values["vertical_alignment"],
                    )

                carriage_row = PhysicalInspectionAnalysis.objects.create(
                    inspection=inspection,
                    consideration_type=PhysicalInspectionAnalysis.CONSIDERATION_DESIGN,
                    option=PhysicalInspectionAnalysis.OPTION_CARRIAGE_WAY_CROSS_SECTIONS,
                    option_description=(request.POST.get("carriage_way_description", "") or "").strip(),
                )
                for index in range(1, 9):
                    PhysicalInspectionCharacteristic.objects.create(
                        analysis=carriage_row,
                        characteristic="No of Carriage Ways",
                        value="2",
                        row_index=index,
                    )

                if physical_values["bridges"]:
                    bridges_row = PhysicalInspectionAnalysis.objects.create(
                        inspection=inspection,
                        consideration_type=PhysicalInspectionAnalysis.CONSIDERATION_DESIGN,
                        option=PhysicalInspectionAnalysis.OPTION_BRIDGES,
                        option_description=(request.POST.get("bridges_description", "") or "").strip(),
                    )
                    PhysicalInspectionCharacteristic.objects.create(
                        analysis=bridges_row,
                        characteristic=physical_values["bridges"],
                        value=physical_values["bridges"],
                    )

                for upload in request.FILES.getlist("supporting_files"):
                    PhysicalInspectionAttachment.objects.create(
                        inspection=inspection,
                        file=upload,
                    )

            return redirect(
                f"{reverse('physical_inspection')}?mode=form&saved=1&inspection={inspection.pk}"
            )

    physical_inspections = (
        PhysicalInspection.objects.select_related("subsegment", "subsegment__segment")
        .prefetch_related("defect_types", "attachments", "analysis_rows__characteristics")
        .order_by("-id")
    )
    physical_total = physical_inspections.count()
    physical_draft_count = physical_inspections.filter(
        status=PhysicalInspection.STATUS_DRAFT
    ).count()
    physical_complete_count = physical_inspections.filter(
        status=PhysicalInspection.STATUS_COMPLETE
    ).count()
    defect_label_map = dict(defect_options)
    physical_draft_rows = []
    physical_complete_rows = []
    for report in physical_inspections[:100]:
        selected_codes = list(report.defect_types.values_list("code", flat=True))
        selected_labels = [defect_label_map.get(code) for code in selected_codes if code in defect_label_map]
        defect_text = ", ".join((label or "").lower() for label in selected_labels if label)
        if not defect_text:
            defect_text = "not specified"

        segment_status_code = getattr(getattr(report.subsegment, "segment", None), "status", "")
        if segment_status_code in {"FF0000", "FF5050", "FF9966"}:
            condition_label = "Intolerable"
            condition_class = "intolerable"
        else:
            condition_label = "Tolerable"
            condition_class = "tolerable"

        row = {
            "report": report,
            "defect_text": defect_text,
            "condition_label": condition_label,
            "condition_class": condition_class,
            "engineer_name": "Engineer Ridwan Bankole",
        }
        if report.status == PhysicalInspection.STATUS_COMPLETE:
            physical_complete_rows.append(row)
        else:
            physical_draft_rows.append(row)

    for idx, row in enumerate(physical_draft_rows):
        row["date_text"] = "2 days" if idx == 0 else "5 days"
    for idx, row in enumerate(physical_complete_rows):
        row["date_text"] = "5 days" if idx == 0 else "5 days"

    current_physical_view = existing_inspection if library_mode == "view" else None
    if library_mode == "view" and current_physical_view is None:
        current_physical_view = physical_inspections.filter(
            status=PhysicalInspection.STATUS_COMPLETE
        ).first()

    physical_view_defect_text = ""
    physical_view_cross_sections = []
    physical_supporting_documents = []
    physical_view_segment_status_text = "No response"
    physical_view_segment_status_class = "neutral"
    if current_physical_view:
        option_rows = {row.option: row for row in current_physical_view.analysis_rows.all()}
        horizontal_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_HORIZONTAL_ALIGNMENT)
        if horizontal_row:
            first = horizontal_row.characteristics.first()
            if first:
                physical_values["horizontal_alignment"] = first.value or first.characteristic
        vertical_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_VERTICAL_ALIGNMENT)
        if vertical_row:
            first = vertical_row.characteristics.first()
            if first:
                physical_values["vertical_alignment"] = first.value or first.characteristic
        bridges_row = option_rows.get(PhysicalInspectionAnalysis.OPTION_BRIDGES)
        if bridges_row:
            first = bridges_row.characteristics.first()
            if first:
                physical_values["bridges"] = first.value or first.characteristic
        carriage_row = option_rows.get(
            PhysicalInspectionAnalysis.OPTION_CARRIAGE_WAY_CROSS_SECTIONS
        )
        if carriage_row:
            carriage_items = (
                carriage_row.characteristics.exclude(row_index__isnull=True)
                .order_by("row_index", "id")
            )
            physical_view_cross_sections = [
                {
                    "label": item.characteristic or "No of Carriage Ways",
                    "value": item.value or "Not provided",
                }
                for item in carriage_items[:8]
            ]
        if not physical_view_cross_sections:
            physical_view_cross_sections = [
                {"label": "No of Carriage Ways", "value": "2"} for _ in range(8)
            ]

        selected_codes = list(current_physical_view.defect_types.values_list("code", flat=True))
        selected_labels = [defect_label_map.get(code) for code in selected_codes if code in defect_label_map]
        physical_view_defect_text = ", ".join(label for label in selected_labels if label) or "Not provided"

        attachments = list(current_physical_view.attachments.all())
        if attachments:
            physical_supporting_documents = [item.file.name.split("/")[-1] for item in attachments]
        else:
            code = current_physical_view.subsegment.code if current_physical_view.subsegment else "A1LAS2-01"
            physical_supporting_documents = [f"{code} Physical Inspection.jpg", f"{code} Physical Inspection.jpg"]

        segment_status_code = getattr(getattr(current_physical_view.subsegment, "segment", None), "status", "")
        if segment_status_code in {"FF0000", "FF5050", "FF9966"}:
            physical_view_segment_status_text = "Intolerable"
            physical_view_segment_status_class = "intolerable"
        elif segment_status_code in {"FFFFCC", "00CC00", "339933", "006600"}:
            physical_view_segment_status_text = "Tolerable"
            physical_view_segment_status_class = "tolerable"

    return render(
        request,
        "website/library.html",
        {
            "active_page": "library",
            "active_library_tab": "physical",
            "library_mode": library_mode,
            "physical_success": physical_success,
            "physical_error": physical_error,
            "physical_values": physical_values,
            "current_physical_inspection": existing_inspection,
            "physical_defect_options": defect_options,
            "physical_horizontal_alignment_options": horizontal_alignment_options,
            "physical_vertical_alignment_options": vertical_alignment_options,
            "physical_bridge_options": bridge_options,
            "physical_cross_sections": list(range(8)),
            "physical_total": physical_total,
            "physical_draft_count": physical_draft_count,
            "physical_complete_count": physical_complete_count,
            "physical_draft_rows": physical_draft_rows,
            "physical_complete_rows": physical_complete_rows,
            "current_physical_view": current_physical_view,
            "physical_view_defect_text": physical_view_defect_text,
            "physical_view_cross_sections": physical_view_cross_sections,
            "physical_supporting_documents": physical_supporting_documents,
            "physical_view_segment_status_text": physical_view_segment_status_text,
            "physical_view_segment_status_class": physical_view_segment_status_class,
        },
    )


def library_solution_design(request):
    return render(
        request,
        "website/library.html",
        {
            "active_page": "library",
            "active_library_tab": "solution",
        },
    )

# def uploads(request):
#     if request.method == "POST":
#         # Placeholder only — real behaviour to be added when you share details
#         # uploaded_file = request.FILES.get("segment_file")
#         return HttpResponse("Upload received (stub). Behaviour to be defined.")
#     return render(request, "website/uploads.html")

# ---- Road Analysis with page-size selector + robust filter preservation (Point 5) ----



# website/views.py
from decimal import Decimal
from urllib.parse import urlencode
from django.db.models import Sum, Count
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404

from all_roads.models import Segment, Route
from all_roads.models import SubSegment  # <-- NEW import
# assume STATUS_BUCKETS, PAGE_SIZE_DEFAULT, PAGE_SIZE_OPTIONS exist in this module

def road_analysis(request):
    qs = Segment.objects.select_related("route", "start_point", "end_point").all()

    # Query params
    selected_route   = request.GET.get("route") or ""
    selected_state   = (request.GET.get("state") or "").strip()
    if selected_state:
        selected_state = selected_state.upper()
    selected_segment = (request.GET.get("segment") or "").strip()
    show_all         = request.GET.get("show") == "all"

    # Enforce mutual exclusivity (route vs state)
    if show_all:
        selected_route = ""
        selected_state = ""
    elif selected_route:
        selected_state = ""
        qs = qs.filter(route__route=selected_route)
    elif selected_state:
        selected_route = ""
        qs = qs.annotate(_normalized_state=Upper(Trim("state"))).filter(_normalized_state=selected_state)

    # Are we viewing subsegments for a specific segment code?
    is_subsegment_view = False
    sub_qs = None
    parent_segment = None

    if selected_segment:
        # case-insensitive exact match; switch to subsegment mode if found
        parent_segment = get_object_or_404(Segment, code__iexact=selected_segment)
        try:
            refresh_segment_and_subsegments(parent_segment)
            parent_segment.refresh_from_db(fields=["avg_speed", "status", "distance", "travel_time"])
        except Exception as exc:
            logger.warning("Unable to refresh segment %s before rendering subsegments: %s", parent_segment.code, exc)
        sub_qs = SubSegment.objects.filter(segment=parent_segment).order_by("position", "id")
        is_subsegment_view = True

    # Aggregates & counts (only meaningful for the normal segment view)
    if not is_subsegment_view:
        agg = qs.aggregate(total_length=Sum("distance"), total_segments=Count("id"))
        total_length   = (agg["total_length"] or Decimal("0.00")).quantize(Decimal("0.01"))
        total_segments = agg["total_segments"] or 0
        counts = {k: qs.filter(status__in=v["codes"]).count() for k, v in STATUS_BUCKETS.items()}
    else:
        # When viewing subsegments, the top-right panel is a graph, so we don't need totals/metrics.
        total_length = Decimal("0.00")
        total_segments = 0
        counts = {"good": 0, "tolerable": 0, "intolerable": 0, "failed": 0, "no_response": 0}

    # Options for selects
    routes = Route.objects.only("route").order_by("route")
    states = (
        Segment.objects.filter(state__isnull=False)
        .annotate(normalized_state=Upper(Trim("state")))
        .filter(~Q(normalized_state=""))
        .order_by("normalized_state")
        .values_list("normalized_state", flat=True)
        .distinct()
    )

    # Page size
    try:
        page_size = int(request.GET.get("page_size") or PAGE_SIZE_DEFAULT)
        if page_size not in PAGE_SIZE_OPTIONS:
            page_size = PAGE_SIZE_DEFAULT
    except (TypeError, ValueError):
        page_size = PAGE_SIZE_DEFAULT

    # Pagination target: segments OR subsegments
    if is_subsegment_view:
        paginator = Paginator(sub_qs, page_size)
    else:
        qs = qs.order_by("route__route", "index", "code")
        paginator = Paginator(qs, page_size)

    page_obj = paginator.get_page(request.GET.get("page") or 1)
    sn_start = page_obj.start_index() - 1

    # Preserve filters across pagination (strip only 'page')
    qd = request.GET.copy()
    qd.pop("page", None)
    filters_qs = qd.urlencode()

    context = {
        # table data (choose which the template renders)
        "segments": (page_obj.object_list if not is_subsegment_view else []),
        "subsegments": (page_obj.object_list if is_subsegment_view else []),

        "page_obj": page_obj,
        "sn_start": sn_start,

        # filters
        "routes": routes,
        "states": list(states),
        "selected_route": selected_route,
        "selected_state": selected_state,
        "selected_segment": selected_segment,
        "show_all": show_all,

        # metrics (for normal view)
        "total_length": total_length,
        "total_segments": total_segments,
        "counts": counts,
        "filters_qs": filters_qs,

        # page size controls
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,

        # view mode
        "is_subsegment_view": is_subsegment_view,
        "parent_segment": parent_segment,
        "active_page": "inventory",
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

SUBSEG_REQUIRED_HEADERS = ["X_START", "Y_START", "X_END", "Y_END"]

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

def _read_subsegment_rows(fileobj, filename):
    """
    Extract the coordinate columns needed for sub-segment uploads.
    """
    name = (filename or "").lower()
    required_norm = _normalize_headers(SUBSEG_REQUIRED_HEADERS)
    norm_to_canon = dict(zip(required_norm, SUBSEG_REQUIRED_HEADERS))

    def _build_from_rows(rows):
        if not rows:
            return [], ["The spreadsheet is empty."]
        headers = _normalize_headers(rows[0])
        idx = {norm_to_canon[h]: headers.index(h) for h in required_norm if h in headers}
        missing = [norm_to_canon[h] for h in required_norm if h not in headers]
        if missing:
            missing_titles = ", ".join(missing).lower()
            return [], [f"Missing column headers: {missing_titles}."]
        out = []
        for i, r in enumerate(rows[1:], start=2):
            if _is_blank_row(r):
                continue
            def cell(h):
                j = idx[h]
                return r[j] if j < len(r or []) else ""
            out.append({
                "X_START": cell("X_START"),
                "Y_START": cell("Y_START"),
                "X_END": cell("X_END"),
                "Y_END": cell("Y_END"),
                "_rownum": i,
            })
        return out, []

    if name.endswith(".csv"):
        fileobj.seek(0)
        data = fileobj.read().decode("utf-8", errors="ignore")
        rows = list(csv.reader(io.StringIO(data)))
        return _build_from_rows(rows)
    elif name.endswith(".xlsx"):
        if openpyxl is None:
            return [], ["Excel support is unavailable on this server (.xlsx)."]
        fileobj.seek(0)
        wb = openpyxl.load_workbook(fileobj, data_only=True)
        ws = wb.active
        rows = [[cell for cell in row] for row in ws.iter_rows(values_only=True)]
        return _build_from_rows(rows)
    elif name.endswith(".xls"):
        if xlrd is None:
            return [], ["Excel support is unavailable on this server (.xls)."]
        fileobj.seek(0)
        book = xlrd.open_workbook(file_contents=fileobj.read())
        sheet = book.sheet_by_index(0)
        rows = [sheet.row_values(i) for i in range(sheet.nrows)]
        return _build_from_rows(rows)
    elif name.endswith(".numbers"):
        return [], ["Apple Numbers files must be exported to CSV or Excel before uploading."]
    else:
        return [], [f"Unsupported file type: {filename}"]

def _process_subsegment_upload(segment_code, start_row, end_row, fileobj):
    errors = []
    seg_code = (segment_code or "").strip()
    if not seg_code:
        return {"created": 0, "replaced": 0, "errors": ["Please select a segment."]}

    try:
        segment_obj = Segment.objects.get(code__iexact=seg_code)
    except Segment.DoesNotExist:
        return {
            "created": 0,
            "replaced": 0,
            "errors": [f"The segment “{seg_code}” was not found. Please check the code and try again."]
        }

    rows, header_errors = _read_subsegment_rows(fileobj, fileobj.name)
    if header_errors:
        return {"created": 0, "replaced": 0, "errors": header_errors}

    if not rows:
        return {"created": 0, "replaced": 0, "errors": ["No sub-segments were found in the spreadsheet."]}

    row_lookup = {row["_rownum"]: row for row in rows}
    selected_rows = []
    missing_rows = []
    for row_num in range(start_row, end_row + 1):
        data = row_lookup.get(row_num)
        if data:
            selected_rows.append(data)
        else:
            missing_rows.append(row_num)

    if missing_rows:
        pretty_rows = ", ".join(str(num) for num in missing_rows)
        return {
            "created": 0,
            "replaced": 0,
            "errors": [f"Rows {pretty_rows} have no data. Update the sheet or adjust the range."]
        }

    cleaned_rows = []
    for row in selected_rows:
        rownum = row.get("_rownum")
        coord_errors_before = len(errors)
        start_lon = _to_decimal(row["X_START"], "x_start", rownum, errors)
        start_lat = _to_decimal(row["Y_START"], "y_start", rownum, errors)
        end_lon   = _to_decimal(row["X_END"], "x_end", rownum, errors)
        end_lat   = _to_decimal(row["Y_END"], "y_end", rownum, errors)
        has_new_error = len(errors) > coord_errors_before

        coord_bad = False
        if not _in_lon_range(start_lon):
            errors.append(f"Row {rownum}: x_start must be between -180 and 180.")
            coord_bad = True
        if not _in_lat_range(start_lat):
            errors.append(f"Row {rownum}: y_start must be between -90 and 90.")
            coord_bad = True
        if not _in_lon_range(end_lon):
            errors.append(f"Row {rownum}: x_end must be between -180 and 180.")
            coord_bad = True
        if not _in_lat_range(end_lat):
            errors.append(f"Row {rownum}: y_end must be between -90 and 90.")
            coord_bad = True

        if has_new_error or coord_bad:
            continue

        cleaned_rows.append({
            "start_lat": start_lat,
            "start_lon": start_lon,
            "end_lat": end_lat,
            "end_lon": end_lon,
            "_rownum": rownum,
        })

    if errors:
        return {"created": 0, "replaced": 0, "errors": errors}

    with transaction.atomic():
        replaced = SubSegment.objects.filter(segment=segment_obj).count()
        SubSegment.objects.filter(segment=segment_obj).delete()
        objs = []
        for position, payload in enumerate(cleaned_rows, start=1):
            objs.append(SubSegment(
                segment=segment_obj,
                position=position,
                code=f"{segment_obj.code}-{position:02d}",
                start_lat=payload["start_lat"],
                start_lon=payload["start_lon"],
                end_lat=payload["end_lat"],
                end_lon=payload["end_lon"],
            ))
        SubSegment.objects.bulk_create(objs)

    return {"created": len(cleaned_rows), "replaced": replaced, "errors": []}

def uploads(request):
    result = None
    sub_result = None

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "subsegments":
            form = UploadSegmentsForm()
            sub_form = UploadSubSegmentsForm(request.POST, request.FILES)
            if sub_form.is_valid():
                sub_result = _process_subsegment_upload(
                    sub_form.cleaned_data["segment"],
                    sub_form.cleaned_data["start_row"],
                    sub_form.cleaned_data["end_row"],
                    sub_form.cleaned_data["segment_code_file"],
                )
            else:
                flat_errors = []
                for field_errors in sub_form.errors.values():
                    flat_errors.extend(field_errors)
                sub_result = {
                    "created": 0,
                    "replaced": 0,
                    "errors": flat_errors,
                }
        else:
            sub_form = UploadSubSegmentsForm()
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
        sub_form = UploadSubSegmentsForm()

    context = {
        "form": form,
        "result": result,
        "sub_form": sub_form,
        "sub_result": sub_result,
        "active_page": "uploads",
    }
    return render(request, "website/uploads.html", context)

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


def motorability_and_condition_subsegments(request):
    """
    AJAX endpoint for motorability_and_condition:
    Case-insensitive segment lookup by code, then return its subsegments.
    """
    segment_code = (request.GET.get("segment") or "").strip()
    if not segment_code:
        return JsonResponse(
            {"ok": False, "message": "Please select a segment code.", "rows": []},
            status=400,
        )

    segment = Segment.objects.filter(code__iexact=segment_code).first()
    if not segment:
        return JsonResponse(
            {"ok": False, "message": f'Segment "{segment_code}" was not found.', "rows": []},
            status=404,
        )

    sub_qs = SubSegment.objects.filter(segment=segment).order_by("position", "id")
    rows = [
        {
            "segment_code": segment.code,
            "code": row.code or f"{segment.code}-{row.position:02d}",
            "position": row.position,
            "start_lat": str(row.start_lat),
            "start_lon": str(row.start_lon),
            "distance": str(row.distance),
            "avg_speed": float(row.avg_speed or 0),
            "status": row.status or "666699",
        }
        for row in sub_qs
    ]

    if not rows:
        return JsonResponse(
            {
                "ok": True,
                "message": f'Segment "{segment.code}" has no subsegments.',
                "rows": [],
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "message": f'Loaded {len(rows)} subsegments for "{segment.code}".',
            "rows": rows,
        }
    )
