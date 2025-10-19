# all_roads/tasks.py
from celery import shared_task
from django.db import transaction
from all_roads.models import Segment
from .services import refresh_segments_from_google

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def refresh_segments_task(self, segment_codes=None):
    """
    Background task: refresh either all segments or a subset by code.
    Retries with exponential backoff on errors (e.g., temporary quota issues).
    """
    qs = Segment.objects.all()
    if segment_codes:
        qs = qs.filter(code__in=segment_codes)

    # Optional: throttle a bit to be gentle on the API (set to 0.2 → ~5 req/s)
    return refresh_segments_from_google(qs, sleep_between=0.0)
