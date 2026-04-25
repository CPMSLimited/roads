from django.core.management.base import BaseCommand
from django.utils import timezone

from all_roads.models import MotorabilitySetting
from all_roads.services import refresh_segments
from website.views import _create_motorability_history_snapshot, _is_motorability_schedule_due


class Command(BaseCommand):
    help = "Run the global motorability refresh if the configured schedule is due."

    def handle(self, *args, **options):
        settings_obj = MotorabilitySetting.get_solo()
        is_due, slot = _is_motorability_schedule_due(settings_obj, timezone.now())
        if not is_due:
            self.stdout.write(self.style.NOTICE("Motorability refresh is not due."))
            return

        try:
            result = refresh_segments()
            failed_count = int(result.get("failed", 0) or 0)
            if failed_count > 0:
                _create_motorability_history_snapshot(
                    run_status="failed",
                    failure_message=f"Scheduled refresh completed with {failed_count} failed segment refreshes.",
                )
                settings_obj.last_run_slot = slot
                settings_obj.save(update_fields=["last_run_slot", "updated"])
                self.stdout.write(
                    self.style.WARNING(
                        f"Motorability refresh recorded as failed. Updated {result.get('updated', 0)} segment(s), "
                        f"failed {failed_count}."
                    )
                )
                return

            _create_motorability_history_snapshot(run_status="success")
            settings_obj.last_run_slot = slot
            settings_obj.save(update_fields=["last_run_slot", "updated"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Motorability refresh complete. Updated {result.get('updated', 0)} segment(s), "
                    f"failed {failed_count}."
                )
            )
        except Exception as exc:
            _create_motorability_history_snapshot(
                run_status="failed",
                failure_message=str(exc) or "Scheduled refresh failed.",
            )
            settings_obj.last_run_slot = slot
            settings_obj.save(update_fields=["last_run_slot", "updated"])
            raise
