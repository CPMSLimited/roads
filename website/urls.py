from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("segments/map-data/", views.segments_map_data, name="segments_map_data"),
    path("road-motorability/", views.road_motorability, name="road_motorability"),
    path("road-inventory/", views.road_inventory, name="road_inventory"),
    path("road-condition/", views.road_condition, name="road_condition"),
    path("library/", views.library_landing, name="library"),
    path("library/road-inventory/", views.library_landing, name="library_road_inventory"),
    path("library/reports/", views.library_reports, name="library_reports"),
    path("library/technical-guide/", views.library_technical_guide, name="library_technical_guide"),
    path("library/user-guide/", views.library_user_guide, name="library_user_guide"),
    path("engineering-admin/root-cause-analysis/", views.library, name="engineering_admin"),
    path("engineering-admin/overview/", views.engineering_admin_overview, name="engineering_admin_overview"),
    path("engineering-admin/physical-inspection/", views.physical_inspection, name="physical_inspection"),
    path("engineering-admin/solution-design/", views.library_solution_design, name="library_solution_design"),
    path("road-analysis/", views.road_analysis, name="road_analysis"),
    path('segments/search/', views.segment_code_search, name='segment_code_search'),
    path(
        "road-condition/subsegments/",
        views.road_condition_subsegments,
        name="road_condition_subsegments",
    ),
]
