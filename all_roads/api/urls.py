from django.urls import path
from . import views

urlpatterns = [
    path('update-segments/', views.update_segment_distances, name='update_segments'),
]
