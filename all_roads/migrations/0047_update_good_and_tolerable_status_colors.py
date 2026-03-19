from django.db import migrations, models


TEMP_CODE = "TMP000"


def forwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    for model in (Segment, SubSegment):
        model.objects.filter(status="00CC00").update(status=TEMP_CODE)
        model.objects.filter(status="339933").update(status="00CC00")
        model.objects.filter(status=TEMP_CODE).update(status="05700B")


def backwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    for model in (Segment, SubSegment):
        model.objects.filter(status="05700B").update(status=TEMP_CODE)
        model.objects.filter(status="00CC00").update(status="339933")
        model.objects.filter(status=TEMP_CODE).update(status="00CC00")


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0046_replace_motorability_status_hex_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="segment",
            name="status",
            field=models.CharField(
                choices=[
                    ("666699", "No response"),
                    ("FF5050", "Failed"),
                    ("FF9966", "Intolerable"),
                    ("00CC00", "Tolerable"),
                    ("05700B", "Good"),
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
                    ("FF5050", "Failed"),
                    ("FF9966", "Intolerable"),
                    ("00CC00", "Tolerable"),
                    ("05700B", "Good"),
                ],
                default="666699",
                help_text="Traffic color code based on average speed",
                max_length=6,
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
