from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0035_segment_characteristics_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="segment",
            name="culverts",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(9)],
            ),
        ),
    ]
