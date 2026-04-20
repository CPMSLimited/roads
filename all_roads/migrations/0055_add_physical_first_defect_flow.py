from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0054_enforce_subsegment_position_limit_to_35"),
    ]

    operations = [
        migrations.AlterField(
            model_name="defect",
            name="workflow_status",
            field=models.CharField(
                choices=[
                    ("physical_draft", "Physical Inspection Draft"),
                    ("rca_draft", "Root Cause Analysis Draft"),
                    ("rca_complete", "Root Cause Analysis Complete"),
                    ("solution_design", "Solution Design"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("repair_ongoing", "Repair ongoing"),
                    ("repair_complete", "Repair complete"),
                ],
                default="physical_draft",
                max_length=32,
            ),
        ),
    ]
