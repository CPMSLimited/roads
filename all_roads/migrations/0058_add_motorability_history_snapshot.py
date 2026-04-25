from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0057_add_motorability_setting"),
    ]

    operations = [
        migrations.CreateModel(
            name="MotorabilityHistorySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_status", models.CharField(choices=[("success", "Success"), ("failed", "Failed")], default="success", max_length=16)),
                ("refresh_run_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("failure_message", models.TextField(blank=True, default="")),
                ("total_segments", models.PositiveIntegerField(default=0)),
                ("good_count", models.PositiveIntegerField(blank=True, null=True)),
                ("good_percentage", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("tolerable_count", models.PositiveIntegerField(blank=True, null=True)),
                ("tolerable_percentage", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("intolerable_count", models.PositiveIntegerField(blank=True, null=True)),
                ("intolerable_percentage", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("failed_count", models.PositiveIntegerField(blank=True, null=True)),
                ("failed_percentage", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("no_response_count", models.PositiveIntegerField(blank=True, null=True)),
                ("no_response_percentage", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("failed_max_speed", models.PositiveSmallIntegerField(default=40)),
                ("intolerable_min_speed", models.PositiveSmallIntegerField(default=40)),
                ("intolerable_max_speed", models.PositiveSmallIntegerField(default=60)),
                ("tolerable_min_speed", models.PositiveSmallIntegerField(default=60)),
                ("tolerable_max_speed", models.PositiveSmallIntegerField(default=80)),
                ("good_min_speed", models.PositiveSmallIntegerField(default=80)),
                ("created", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-refresh_run_at", "-id"],
            },
        ),
    ]
