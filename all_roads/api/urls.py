from django.urls import path
from . import views

urlpatterns = [
    path('all_segments/', views.all_segments_view, name='all_segments'),  
    path('update-segments/queue/', views.queue_refresh, name='queue_refresh'),
    path('tasks/<uuid:task_id>/', views.task_status, name='task_status'),
]
