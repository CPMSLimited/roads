from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0048_expand_subsegment_position_limit_to_100"),
    ]

    operations = [
        migrations.AlterField(
            model_name="library",
            name="entry_type",
            field=models.CharField(
                choices=[
                    ("report_upload", "Report Upload"),
                    ("technical_guide", "Technical Guide"),
                    ("user_guide", "User Guide"),
                    ("root_cause_analysis", "Root Cause Analysis"),
                    ("physical_inspection", "Physical Inspection"),
                    ("solution_design", "Solution Design"),
                ],
                max_length=32,
            ),
        ),
    ]
