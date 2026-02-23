from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("road-inventory/", views.road_inventory, name="road_inventory"),
    path("motorability-and-condition/", views.motorability_and_condition, name="motorability_and_condition"),
    path("library/", views.library, name="library"),
    path("library/overview/", views.library_overview, name="library_overview"),
    path("physical-inspection/", views.physical_inspection, name="physical_inspection"),
    path("library/solution-design/", views.library_solution_design, name="library_solution_design"),
    path("road-analysis/", views.road_analysis, name="road_analysis"),
    path("uploads/", views.uploads, name="uploads"),
    path('segments/search/', views.segment_code_search, name='segment_code_search'),
    path(
        "motorability-and-condition/subsegments/",
        views.motorability_and_condition_subsegments,
        name="motorability_and_condition_subsegments",
    ),
]
