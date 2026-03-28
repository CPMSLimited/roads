import re

from django.db import migrations


ONE_DIGIT_SUFFIX_RE = re.compile(r"^(?P<prefix>.*?)(?P<suffix>\d)$")


def normalize_segment_code(value):
    code = str(value or "").strip().upper()
    if not code:
        return code
    match = ONE_DIGIT_SUFFIX_RE.match(code)
    if match:
        return f"{match.group('prefix')}0{match.group('suffix')}"
    return code


def forwards(apps, schema_editor):
    Segment = apps.get_model("all_roads", "Segment")
    SubSegment = apps.get_model("all_roads", "SubSegment")

    segments_to_update = []
    changed_segment_ids = set()
    for segment in Segment.objects.all().only("id", "code", "index"):
        normalized = normalize_segment_code(segment.code)
        if normalized != segment.code:
            segment.code = normalized
            suffix = normalized[-2:]
            segment.index = str(int(suffix))
            segments_to_update.append(segment)
            changed_segment_ids.add(segment.id)

    if segments_to_update:
        Segment.objects.bulk_update(segments_to_update, ["code", "index"])

    subsegments_to_update = []
    qs = SubSegment.objects.select_related("segment").all().only("id", "code", "position", "segment__id", "segment__code")
    for subsegment in qs:
        expected = f"{subsegment.segment.code}-{subsegment.position:02d}"
        if subsegment.code != expected:
            subsegment.code = expected
            subsegments_to_update.append(subsegment)

    if subsegments_to_update:
        SubSegment.objects.bulk_update(subsegments_to_update, ["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0049_add_report_upload_entry_type"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
