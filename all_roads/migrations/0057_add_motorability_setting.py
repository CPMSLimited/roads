from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0056_rebucket_motorability_thresholds_40_60_80"),
    ]

    operations = [
        migrations.CreateModel(
            name="MotorabilitySetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("singleton_guard", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("refresh_frequency", models.CharField(choices=[("weekly", "Weekly"), ("monthly", "Monthly")], default="weekly", max_length=16)),
                ("refresh_weekday", models.CharField(choices=[("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday"), ("sunday", "Sunday")], default="monday", max_length=16)),
                ("refresh_month_day", models.PositiveSmallIntegerField(default=1)),
                ("refresh_hour", models.PositiveSmallIntegerField(default=0)),
                ("refresh_timezone", models.CharField(default="Africa/Lagos", max_length=64)),
                ("last_run_slot", models.CharField(blank=True, default="", max_length=64)),
                ("failed_max_speed", models.PositiveSmallIntegerField(default=40)),
                ("intolerable_min_speed", models.PositiveSmallIntegerField(default=40)),
                ("intolerable_max_speed", models.PositiveSmallIntegerField(default=60)),
                ("tolerable_min_speed", models.PositiveSmallIntegerField(default=60)),
                ("tolerable_max_speed", models.PositiveSmallIntegerField(default=80)),
                ("good_min_speed", models.PositiveSmallIntegerField(default=80)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["id"]},
        ),
    ]
