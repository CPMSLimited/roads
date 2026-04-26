from django.db import migrations, models


ZONE_NAMES = [
    "West",
    "East",
    "North-Central I",
    "North-Central II",
    "North-West I",
    "North-West II",
    "South-West I",
    "South-West II",
    "South-South II",
    "North-East I",
    "North-East II",
    "South-East I",
    "South-East II",
    "South-South I",
]


def create_zones(apps, schema_editor):
    Zone = apps.get_model("all_roads", "Zone")
    for zone_name in ZONE_NAMES:
        Zone.objects.get_or_create(zone=zone_name)


def delete_zones(apps, schema_editor):
    Zone = apps.get_model("all_roads", "Zone")
    Zone.objects.filter(zone__in=ZONE_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0058_add_motorability_history_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="Zone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("zone", models.CharField(max_length=32, unique=True)),
                ("states", models.ManyToManyField(blank=True, related_name="zones", to="all_roads.state")),
            ],
        ),
        migrations.RunPython(create_zones, delete_zones),
    ]
