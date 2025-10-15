from django.urls import path
from . import views

urlpatterns = [
    path('update-segments/', views.update_segment_distances, name='update_segments'),
    path('api/segments/', views.all_segments_view, name='all_segments'),  
]
