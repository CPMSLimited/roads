from django.db import migrations


def _status_from_speed(speed):
    try:
        speed = float(speed or 0)
    except (TypeError, ValueError):
        speed = 0
    if speed <= 0:
        return "666699"
    if speed < 40:
        return "FF5050"
    if speed < 60:
        return "FF9966"
    if speed < 80:
        return "00CC00"
    return "05700B"


def _rebucket_model(apps, model_name):
    model = apps.get_model("all_roads", model_name)
    to_update = []
    for obj in model.objects.all().only("id", "avg_speed", "status").iterator(chunk_size=500):
        next_status = _status_from_speed(obj.avg_speed)
        if obj.status != next_status:
            obj.status = next_status
            to_update.append(obj)
    if to_update:
        model.objects.bulk_update(to_update, ["status"])


def forwards(apps, schema_editor):
    _rebucket_model(apps, "Segment")
    _rebucket_model(apps, "SubSegment")


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0055_add_physical_first_defect_flow"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
