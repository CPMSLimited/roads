from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0043_rebucket_motorability_statuses"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="subsegment",
            name="ck_subsegment_position_1_25",
        ),
        migrations.AlterField(
            model_name="subsegment",
            name="position",
            field=models.PositiveSmallIntegerField(
                help_text="Order of this sub-segment within its parent segment (1–50).",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(50),
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="subsegment",
            constraint=models.CheckConstraint(
                check=models.Q(("position__gte", 1), ("position__lte", 50)),
                name="ck_subsegment_position_1_50",
            ),
        ),
    ]
