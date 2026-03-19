from django.db import migrations, models


STATUS_REMAP = {
    "F70202": "FF5050",
    "FF8D28": "FF9966",
    "2A6FDD": "339933",
    "1F8A70": "00CC00",
}


def forwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    for model in (Segment, SubSegment):
        for old_code, new_code in STATUS_REMAP.items():
            model.objects.filter(status=old_code).update(status=new_code)


def backwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")
    reverse_map = {value: key for key, value in STATUS_REMAP.items()}

    for model in (Segment, SubSegment):
        for old_code, new_code in reverse_map.items():
            model.objects.filter(status=old_code).update(status=new_code)


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0045_clear_legacy_motorability_hex_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="segment",
            name="status",
            field=models.CharField(
                choices=[
                    ("666699", "No response"),
                    ("FF5050", "Failed (<60 km/h)"),
                    ("FF9966", "Intolerable (60 to <70 km/h)"),
                    ("339933", "Tolerable (70 to <80 km/h)"),
                    ("00CC00", "Good (>=80 km/h)"),
                ],
                default="666699",
                help_text="Traffic color code based on average speed",
                max_length=6,
            ),
        ),
        migrations.AlterField(
            model_name="subsegment",
            name="status",
            field=models.CharField(
                choices=[
                    ("666699", "No response"),
                    ("FF5050", "Failed (<60 km/h)"),
                    ("FF9966", "Intolerable (60 to <70 km/h)"),
                    ("339933", "Tolerable (70 to <80 km/h)"),
                    ("00CC00", "Good (>=80 km/h)"),
                ],
                default="666699",
                help_text="Traffic color code based on average speed",
                max_length=6,
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
