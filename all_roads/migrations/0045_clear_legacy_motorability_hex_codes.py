from decimal import Decimal, InvalidOperation

from django.db import migrations


LEGACY_STATUS_CODES = {"FF0000", "FF5050", "FF9966", "FFFFCC", "00CC00", "339933", "006600"}


def _status_from_speed(speed):
    if speed is None:
        return "666699"
    try:
        speed = Decimal(speed)
    except (InvalidOperation, TypeError, ValueError):
        return "666699"
    if speed < 1:
        return "666699"
    if speed < 60:
        return "F70202"
    if speed < 70:
        return "FF8D28"
    if speed < 80:
        return "2A6FDD"
    return "1F8A70"


def forwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    for model in (Segment, SubSegment):
        queryset = model.objects.filter(status__in=LEGACY_STATUS_CODES).only("id", "avg_speed", "status")
        for obj in queryset.iterator(chunk_size=500):
            obj.status = _status_from_speed(obj.avg_speed)
            obj.save(update_fields=["status"])


def backwards(apps, schema_editor):
    # Legacy colors are being removed; there is no safe reverse mapping.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0044_expand_subsegment_position_limit_to_50"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
