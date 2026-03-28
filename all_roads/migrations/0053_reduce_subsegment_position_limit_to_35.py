from django.db import migrations, models, transaction
import django.core.validators
from django.db.models import Count


SEGMENT_CHUNK_SIZE = 100


def build_signature(subsegment):
    return (
        str(subsegment.start_lat) if subsegment.start_lat is not None else "",
        str(subsegment.start_lon) if subsegment.start_lon is not None else "",
        str(subsegment.end_lat) if subsegment.end_lat is not None else "",
        str(subsegment.end_lon) if subsegment.end_lon is not None else "",
        str(subsegment.distance) if subsegment.distance is not None else "",
    )


def find_repeating_prefix_length(signatures, min_repeat_items=2):
    total = len(signatures)
    if total < 2:
        return None
    for prefix_len in range(1, total):
        repeated_count = total - prefix_len
        if repeated_count < min_repeat_items:
            continue
        if all(signatures[idx] == signatures[idx % prefix_len] for idx in range(prefix_len, total)):
            return prefix_len
    return None


def cleanup_repeated_subsegments(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    segment_ids = (
        Segment.objects.annotate(subsegment_count=Count("subsegments"))
        .filter(subsegment_count__gt=1)
        .order_by("id")
        .values_list("id", flat=True)
    )

    for segment_id in segment_ids.iterator(chunk_size=SEGMENT_CHUNK_SIZE):
        subsegments = list(
            SubSegment.objects.select_related("segment").filter(segment_id=segment_id)
            .order_by("position", "id")
        )
        signatures = [build_signature(subsegment) for subsegment in subsegments]
        prefix_len = find_repeating_prefix_length(signatures)
        if prefix_len is None:
            continue

        keep = subsegments[:prefix_len]
        delete_ids = [subsegment.id for subsegment in subsegments[prefix_len:]]
        for position, subsegment in enumerate(keep, start=1):
            subsegment.position = position
            subsegment.code = f"{subsegment.segment.code}-{position:02d}"

        with transaction.atomic():
            if delete_ids:
                SubSegment.objects.filter(id__in=delete_ids).delete()
            if keep:
                SubSegment.objects.bulk_update(keep, ["position", "code"], batch_size=SEGMENT_CHUNK_SIZE)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("all_roads", "0052_repair_segment_code_zero_padding"),
    ]

    operations = [
        migrations.RunPython(cleanup_repeated_subsegments, migrations.RunPython.noop),
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
        migrations.RemoveConstraint(
            model_name="subsegment",
            name="ck_subsegment_position_1_100",
        ),
        migrations.AddConstraint(
            model_name="subsegment",
            constraint=models.CheckConstraint(
                check=models.Q(position__gte=1) & models.Q(position__lte=35),
                name="ck_subsegment_position_1_35",
            ),
        ),
    ]
