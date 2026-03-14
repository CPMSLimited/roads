from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0041_alter_segment_status_alter_subsegment_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="segment",
            name="status",
            field=models.CharField(
                choices=[
                    ("666699", "No response"),
                    ("F70202", "Failed (<60 km/h)"),
                    ("FF8D28", "Intolerable (60 to <70 km/h)"),
                    ("2A6FDD", "Tolerable (70 to <80 km/h)"),
                    ("1F8A70", "Good (>=80 km/h)"),
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
                    ("F70202", "Failed (<60 km/h)"),
                    ("FF8D28", "Intolerable (60 to <70 km/h)"),
                    ("2A6FDD", "Tolerable (70 to <80 km/h)"),
                    ("1F8A70", "Good (>=80 km/h)"),
                ],
                default="666699",
                help_text="Traffic color code based on average speed",
                max_length=6,
            ),
        ),
    ]
