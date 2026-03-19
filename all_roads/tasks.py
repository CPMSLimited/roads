import os

from celery import shared_task
from all_roads.models import Segment
from .services import refresh_segments_from_google
from website.library_upload_jobs import process_new_subsegments_upload

@shared_task(name="all_roads.tasks.refresh_segments_task")
def refresh_segments_task(codes=None, sleep_between=0.0):
    qs = Segment.objects.all()
    if codes:
        qs = qs.filter(code__in=codes)
    return refresh_segments_from_google(qs, sleep_between=sleep_between)


@shared_task(bind=True, name="all_roads.tasks.import_new_subsegments_task")
def import_new_subsegments_task(self, temp_path, original_name, chunk_size=1000):
    def _progress(processed_rows, summary):
        total_rows = int(summary.get("rows_found") or 0)
        percent = int((processed_rows / total_rows) * 100) if total_rows else 0
        self.update_state(
            state="PROGRESS",
            meta={
                "processed_rows": processed_rows,
                "total_rows": total_rows,
                "created": int(summary.get("created") or 0),
                "skipped": int(summary.get("skipped") or 0),
                "percent": percent,
            },
        )

    try:
        with open(temp_path, "rb") as fileobj:
            return process_new_subsegments_upload(
                fileobj,
                original_name,
                chunk_size=chunk_size,
                progress_callback=_progress,
            )
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

"""
curl -X POST https://cpmsferma.com/api/update-segments/queue/ \
  -H 'Content-Type: application/json' \
  -d '{"codes":["F100LAS1","F102RIV2"]}'

"""

# @shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
# def refresh_segments_task(self, segment_codes=None):
#     """
#     Background task: refresh either all segments or a subset by code.
#     Retries with exponential backoff on errors (e.g., temporary quota issues).
#     """
#     qs = Segment.objects.all()
#     if segment_codes:
#         qs = qs.filter(code__in=segment_codes)

#     # Optional: throttle a bit to be gentle on the API (set to 0.2 → ~5 req/s)
#     return refresh_segments_from_google(qs, sleep_between=0.0)
