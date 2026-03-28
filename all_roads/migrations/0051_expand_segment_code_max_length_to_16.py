from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0050_normalize_segment_codes_to_two_digits"),
    ]

    operations = [
        migrations.AlterField(
            model_name="segment",
            name="code",
            field=models.CharField(max_length=16, unique=True),
        ),
    ]
