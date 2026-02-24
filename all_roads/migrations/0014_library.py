from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0013_defecttype_physicalinspection_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Library",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("technical_guide", "Technical Guide"),
                            ("user_guide", "User Guide"),
                            ("root_cause_analysis", "Root Cause Analysis"),
                            ("physical_inspection", "Physical Inspection"),
                            ("solution_design", "Solution Design"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "file_type",
                    models.CharField(
                        choices=[
                            ("document", "Document"),
                            ("spreadsheet", "Spreadsheet"),
                            ("pdf", "PDF"),
                            ("csv", "CSV"),
                            ("image", "Image"),
                            ("presentation", "Presentation"),
                            ("archive", "Archive"),
                            ("geo_data", "Geo Data"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                ("file", models.FileField(upload_to="library/files/")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created", "-id"]},
        ),
    ]
