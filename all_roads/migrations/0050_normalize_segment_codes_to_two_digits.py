import re

from django.db import migrations


ONE_DIGIT_SUFFIX_RE = re.compile(r"^(?P<prefix>.*?)(?P<suffix>\d)$")
CHUNK_SIZE = 500


def normalize_segment_code(value):
    code = str(value or "")
    if not code:
        return code
    match = ONE_DIGIT_SUFFIX_RE.match(code)
    if match:
        return f"{match.group('prefix')}0{match.group('suffix')}"
    return code


def flush_batch(model, batch, fields):
    if batch:
        model.objects.bulk_update(batch, fields, batch_size=CHUNK_SIZE)
        batch.clear()


def forwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    segments_to_update = []
    for segment in Segment.objects.all().only("id", "code", "index").order_by("id").iterator(chunk_size=CHUNK_SIZE):
        normalized = normalize_segment_code(segment.code)
        if normalized != segment.code:
            segment.code = normalized
            suffix = normalized[-2:]
            segment.index = str(int(suffix))
            segments_to_update.append(segment)
            if len(segments_to_update) >= CHUNK_SIZE:
                flush_batch(Segment, segments_to_update, ["code", "index"])

    flush_batch(Segment, segments_to_update, ["code", "index"])

    subsegments_to_update = []
    qs = (
        SubSegment.objects.select_related("segment")
        .all()
        .only("id", "code", "position", "segment__id", "segment__code")
        .order_by("id")
        .iterator(chunk_size=CHUNK_SIZE)
    )
    for subsegment in qs:
        expected = f"{subsegment.segment.code}-{subsegment.position:02d}"
        if subsegment.code != expected:
            subsegment.code = expected
            subsegments_to_update.append(subsegment)
            if len(subsegments_to_update) >= CHUNK_SIZE:
                flush_batch(SubSegment, subsegments_to_update, ["code"])

    flush_batch(SubSegment, subsegments_to_update, ["code"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("all_roads", "0049_add_report_upload_entry_type"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
