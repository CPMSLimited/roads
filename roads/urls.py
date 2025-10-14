from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # For serving media files
from django.conf.urls.static import static  # For serving media files
from all_roads import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path("", include("all_roads.api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
