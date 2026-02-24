from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0014_library"),
    ]

    operations = [
        migrations.AlterField(
            model_name="library",
            name="file_type",
            field=models.CharField(
                choices=[
                    ("document", "Document"),
                    ("spreadsheet", "Spreadsheet"),
                    ("pdf", "PDF"),
                    ("csv", "CSV"),
                    ("image", "Image"),
                    ("presentation", "Presentation"),
                    ("geo_data", "Geo Data"),
                    ("other", "Other"),
                ],
                max_length=20,
            ),
        ),
    ]
