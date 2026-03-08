from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0036_segment_culverts"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="end_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="route_end_points",
                to="all_roads.address",
            ),
        ),
        migrations.AddField(
            model_name="route",
            name="start_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="route_start_points",
                to="all_roads.address",
            ),
        ),
    ]
