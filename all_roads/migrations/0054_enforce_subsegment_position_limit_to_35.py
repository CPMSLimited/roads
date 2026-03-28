import django.core.validators
from django.db import migrations, models, transaction


SEGMENT_CHUNK_SIZE = 100


DROP_OLD_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_subsegment_position_1_100'
          AND conrelid = 'sub_segments'::regclass
    ) THEN
        ALTER TABLE sub_segments DROP CONSTRAINT ck_subsegment_position_1_100;
    END IF;
END $$;
"""


ADD_NEW_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_subsegment_position_1_35'
          AND conrelid = 'sub_segments'::regclass
    ) THEN
        ALTER TABLE sub_segments
        ADD CONSTRAINT ck_subsegment_position_1_35
        CHECK (position >= 1 AND position <= 35);
    END IF;
END $$;
"""


DROP_NEW_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_subsegment_position_1_35'
          AND conrelid = 'sub_segments'::regclass
    ) THEN
        ALTER TABLE sub_segments DROP CONSTRAINT ck_subsegment_position_1_35;
    END IF;
END $$;
"""


ADD_OLD_CONSTRAINT_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_subsegment_position_1_100'
          AND conrelid = 'sub_segments'::regclass
    ) THEN
        ALTER TABLE sub_segments
        ADD CONSTRAINT ck_subsegment_position_1_100
        CHECK (position >= 1 AND position <= 100);
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("all_roads", "0053_reduce_subsegment_position_limit_to_35"),
    ]

    operations = [
        migrations.RunPython(
            code=lambda apps, schema_editor: trim_subsegments_to_35(apps),
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(DROP_OLD_CONSTRAINT_SQL, reverse_sql=ADD_OLD_CONSTRAINT_SQL),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="subsegment",
                    name="ck_subsegment_position_1_100",
                ),
            ],
        ),
        migrations.AlterField(
            model_name="subsegment",
            name="position",
            field=models.PositiveSmallIntegerField(
                help_text="Order of this sub-segment within its parent segment (1–35).",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(35),
                ],
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(ADD_NEW_CONSTRAINT_SQL, reverse_sql=DROP_NEW_CONSTRAINT_SQL),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="subsegment",
                    constraint=models.CheckConstraint(
                        check=models.Q(position__gte=1) & models.Q(position__lte=35),
                        name="ck_subsegment_position_1_35",
                    ),
                ),
            ],
        ),
    ]


def trim_subsegments_to_35(apps):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    segment_ids = (
        Segment.objects.order_by("id").values_list("id", flat=True)
    )

    for segment_id in segment_ids.iterator(chunk_size=SEGMENT_CHUNK_SIZE):
        subsegments = list(
            SubSegment.objects.select_related("segment")
            .filter(segment_id=segment_id)
            .order_by("position", "id")
        )
        if len(subsegments) <= 35:
            continue

        keep = subsegments[:35]
        delete_ids = [subsegment.id for subsegment in subsegments[35:]]

        with transaction.atomic():
            for subsegment in keep:
                subsegment.code = f"TMP-{subsegment.id}"
            if keep:
                SubSegment.objects.bulk_update(keep, ["code"], batch_size=SEGMENT_CHUNK_SIZE)

            if delete_ids:
                SubSegment.objects.filter(id__in=delete_ids).delete()

            for position, subsegment in enumerate(keep, start=1):
                subsegment.position = position
                subsegment.code = f"{subsegment.segment.code}-{position:02d}"
            if keep:
                SubSegment.objects.bulk_update(keep, ["position", "code"], batch_size=SEGMENT_CHUNK_SIZE)
