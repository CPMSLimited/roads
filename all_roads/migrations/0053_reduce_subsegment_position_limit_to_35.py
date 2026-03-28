from django.db import migrations, transaction
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


def cleanup_duplicate_subsegments(apps, schema_editor):
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
        seen_signatures = set()
        keep = []
        delete_ids = []
        for subsegment in subsegments:
            signature = build_signature(subsegment)
            if signature in seen_signatures:
                delete_ids.append(subsegment.id)
                continue
            seen_signatures.add(signature)
            keep.append(subsegment)

        if not delete_ids:
            continue

        with transaction.atomic():
            # First move kept rows to temporary unique codes so final renumbering
            # cannot collide with existing duplicate rows that still hold the target code.
            for offset, subsegment in enumerate(keep, start=1):
                subsegment.code = f"TMP-{subsegment.id}"
                subsegment.position = 1000 + offset
            if keep:
                SubSegment.objects.bulk_update(keep, ["code", "position"], batch_size=SEGMENT_CHUNK_SIZE)

            if delete_ids:
                SubSegment.objects.filter(id__in=delete_ids).delete()

            for position, subsegment in enumerate(keep, start=1):
                subsegment.position = position
                subsegment.code = f"{subsegment.segment.code}-{position:02d}"
                subsegment.save(update_fields=["position", "code"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("all_roads", "0052_repair_segment_code_zero_padding"),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_subsegments, migrations.RunPython.noop),
    ]
