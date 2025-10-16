from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("road-analysis/", views.road_analysis, name="road_analysis"),
    path("uploads/", views.uploads, name="uploads"),
]
