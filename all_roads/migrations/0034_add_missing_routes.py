from django.db import migrations


MISSING_ROUTES = [
    "A3-1",
    "A4-4",
    "A4-5",
    "A4-6",
    "F210",
    "F236",
    "F237",
    "F238",
    "F239",
    "F246",
]


def add_missing_routes(apps, schema_editor):
    Road = apps.get_model("all_roads", "Road")
    Route = apps.get_model("all_roads", "Route")

    for code in MISSING_ROUTES:
        road_code = code[0]
        road_obj, _ = Road.objects.get_or_create(road=road_code)
        Route.objects.get_or_create(
            route=code,
            defaults={
                "road": road_obj,
                "index": "",
                "details": "",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0033_route_details"),
    ]

    operations = [
        migrations.RunPython(add_missing_routes, migrations.RunPython.noop),
    ]

