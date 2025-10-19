from django.urls import path
from . import views

urlpatterns = [
    path('all_segments/', views.all_segments_view, name='all_segments'),  
    path('update-segments/', views.update_segment_distances, name='update_segments'),
    path('update-segments/queue/', views.queue_update_segments, name='queue_update_segments'),
    path('update-segments/status/<uuid:task_id>/', views.task_status, name='task_status'),
]
