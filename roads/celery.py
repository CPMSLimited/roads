import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "roads.settings")

app = Celery("roads")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  # finds tasks.py in your apps
