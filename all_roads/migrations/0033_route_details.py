from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0032_defect_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="details",
            field=models.TextField(blank=True, default=""),
        ),
    ]

