from decimal import Decimal

from django.db import migrations


def _status_from_speed(speed):
    if speed is None:
        return "666699"
    speed = Decimal(speed)
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
        for obj in model.objects.all().only("id", "avg_speed", "status").iterator(chunk_size=500):
            new_status = _status_from_speed(obj.avg_speed)
            if obj.status != new_status:
                obj.status = new_status
                obj.save(update_fields=["status"])


def backwards(apps, schema_editor):
    # Old multi-band status values cannot be reliably reconstructed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0042_alter_segment_status_alter_subsegment_status"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
