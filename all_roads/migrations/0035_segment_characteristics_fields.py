from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0034_add_missing_routes"),
    ]

    operations = [
        migrations.AddField(
            model_name="segment",
            name="bridges",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
        migrations.AddField(
            model_name="segment",
            name="carriages",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
        migrations.AddField(
            model_name="segment",
            name="junctions",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
        migrations.AddField(
            model_name="segment",
            name="lanes",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
        migrations.AddField(
            model_name="segment",
            name="pavement_type",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="segment",
            name="settlement_type",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
