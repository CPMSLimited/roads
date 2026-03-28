import csv
import io
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max
from django.db.models.functions import Trim, Upper

from all_roads.models import Segment, SubSegment, normalize_segment_code

try:
    import openpyxl
except Exception:
    openpyxl = None

try:
    import xlrd
except Exception:
    xlrd = None


SUBSEGMENT_UPLOAD_REQUIRED_HEADERS = [
    "SEGMENT",
    "LENGTH",
    "X_START",
    "Y_START",
    "X_END",
    "Y_END",
]

SUBSEGMENT_UPLOAD_HEADER_ALIASES = {
    "SEGMENT": {"segment"},
    "LENGTH": {"length"},
    "X_START": {"x start", "x_start", "x-start", "xstart"},
    "Y_START": {"y start", "y_start", "y-start", "ystart"},
    "X_END": {"x end", "x_end", "x-end", "xend"},
    "Y_END": {"y end", "y_end", "y-end", "yend"},
}


def _normalize_header_token(value):
    value = (value or "").strip().lower()
    value = value.replace("\ufeff", "")
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _is_blank_row(cells):
    if not cells:
        return True
    for cell in cells:
        if cell is None:
            continue
        if isinstance(cell, (int, float)):
            return False
        if str(cell).strip() != "":
            return False
    return True


def _to_decimal_or_none(value):
    try:
        if value is None:
            return None
        parsed = str(value).strip()
        if parsed == "":
            return None
        return Decimal(parsed)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_decimal_required(value, rownum, label, errors, allow_blank_default=None):
    parsed = _to_decimal_or_none(value)
    if parsed is None:
        raw = str(value).strip() if value is not None else ""
        if raw == "" and allow_blank_default is not None:
            return allow_blank_default
        errors.append(f"Row {rownum}: invalid value for {label}.")
        return None
    return parsed


def _in_lat_range(val):
    return val is not None and Decimal("-90") <= val <= Decimal("90")


def _in_lon_range(val):
    return val is not None and Decimal("-180") <= val <= Decimal("180")


def read_new_subsegment_rows(fileobj, filename):
    name = (filename or "").lower()

    def _sniff_csv_dialect(data):
        sample = data[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except Exception:
            return csv.excel

    def _build_from_rows(rows):
        if not rows:
            return [], ["The spreadsheet is empty."]

        header_map = {}
        for idx, raw_header in enumerate(rows[0]):
            token = _normalize_header_token(raw_header)
            if not token:
                continue
            for canonical, aliases in SUBSEGMENT_UPLOAD_HEADER_ALIASES.items():
                if token in aliases and canonical not in header_map:
                    header_map[canonical] = idx
                    break

        missing = [h for h in SUBSEGMENT_UPLOAD_REQUIRED_HEADERS if h not in header_map]
        if missing:
            return [], [f"Missing headers: {', '.join(missing)}"]

        def _cell(row, canonical):
            col = header_map.get(canonical)
            if col is None or col >= len(row):
                return ""
            return row[col]

        out = []
        for rownum, row in enumerate(rows[1:], start=2):
            if _is_blank_row(row):
                continue
            out.append(
                {
                    "SEGMENT": _cell(row, "SEGMENT"),
                    "LENGTH": _cell(row, "LENGTH"),
                    "X_START": _cell(row, "X_START"),
                    "Y_START": _cell(row, "Y_START"),
                    "X_END": _cell(row, "X_END"),
                    "Y_END": _cell(row, "Y_END"),
                    "_rownum": rownum,
                }
            )
        return out, []

    if name.endswith(".csv"):
        fileobj.seek(0)
        data = fileobj.read().decode("utf-8", errors="ignore")
        dialect = _sniff_csv_dialect(data)
        rows = list(csv.reader(io.StringIO(data), dialect=dialect))
        return _build_from_rows(rows)

    if name.endswith(".xlsx"):
        if openpyxl is None:
            return [], ["openpyxl not installed (required for .xlsx)"]
        fileobj.seek(0)
        wb = openpyxl.load_workbook(fileobj, data_only=True)
        ws = wb.active
        rows = [[cell for cell in row] for row in ws.iter_rows(values_only=True)]
        return _build_from_rows(rows)

    if name.endswith(".xls"):
        if xlrd is None:
            return [], ["xlrd not installed (required for .xls)"]
        fileobj.seek(0)
        book = xlrd.open_workbook(file_contents=fileobj.read())
        sheet = book.sheet_by_index(0)
        rows = [sheet.row_values(i) for i in range(sheet.nrows)]
        return _build_from_rows(rows)

    return [], [f"Unsupported file type: {filename}"]


def process_new_subsegments_upload(fileobj, filename, chunk_size=1000, progress_callback=None):
    rows, read_errors = read_new_subsegment_rows(fileobj, filename)
    summary = {
        "created": 0,
        "created_details": [],
        "skipped": 0,
        "skipped_details": [],
        "errors": [],
        "rows_found": len(rows),
    }
    if read_errors:
        summary["errors"].extend(read_errors)
        return summary

    unique_segment_codes = {
        str(row.get("SEGMENT") or "").strip().upper()
        for row in rows
        if str(row.get("SEGMENT") or "").strip()
    }
    segments = (
        Segment.objects.annotate(code_norm=Upper(Trim("code")))
        .filter(code_norm__in=unique_segment_codes)
        .only("id", "code")
    )
    segment_map = {segment.code_norm: segment for segment in segments}

    if segment_map:
        max_positions = {
            row["segment_id"]: int(row["max_position"] or 0)
            for row in (
                SubSegment.objects.filter(segment_id__in=[segment.id for segment in segment_map.values()])
                .values("segment_id")
                .annotate(max_position=Max("position"))
            )
        }
    else:
        max_positions = {}

    segment_position_counter = {
        code: max_positions.get(segment.id, 0)
        for code, segment in segment_map.items()
    }
    pending = []

    def _report_progress(processed_rows):
        if progress_callback:
            progress_callback(processed_rows, summary)

    def _flush_pending():
        nonlocal pending
        if not pending:
            return
        objs = [entry["obj"] for entry in pending]
        try:
            with transaction.atomic():
                SubSegment.objects.bulk_create(objs, batch_size=chunk_size)
            for entry in pending:
                summary["created"] += 1
                summary["created_details"].append(entry["detail"])
        except Exception as exc:
            for entry in pending:
                try:
                    entry["obj"].save(force_insert=True)
                    summary["created"] += 1
                    summary["created_details"].append(entry["detail"])
                except Exception as row_exc:
                    summary["skipped"] += 1
                    summary["skipped_details"].append(
                        f"Row {entry['rownum']}: skipped because subsegment {entry['code']} could not be created."
                    )
                    summary["errors"].append(
                        f"Row {entry['rownum']}: failed to create subsegment {entry['code']}. ({row_exc or exc})"
                    )
        pending = []

    for processed_rows, row in enumerate(rows, start=1):
        rownum = row.get("_rownum")
        segment_code = normalize_segment_code(row.get("SEGMENT"))
        if not segment_code:
            summary["skipped"] += 1
            summary["skipped_details"].append(f"Row {rownum}: skipped because Segment is blank.")
            summary["errors"].append(f"Row {rownum}: Segment is blank.")
            _report_progress(processed_rows)
            continue

        segment_obj = segment_map.get(segment_code)
        if segment_obj is None:
            summary["skipped"] += 1
            summary["skipped_details"].append(
                f"Row {rownum}: skipped because segment {segment_code} was not found."
            )
            summary["errors"].append(f"Row {rownum}: segment {segment_code} was not found.")
            _report_progress(processed_rows)
            continue

        row_errors = []
        x_start = _parse_decimal_required(row.get("X_START"), rownum, "X_Start", row_errors)
        y_start = _parse_decimal_required(row.get("Y_START"), rownum, "Y_Start", row_errors)
        x_end = _parse_decimal_required(row.get("X_END"), rownum, "X_End", row_errors)
        y_end = _parse_decimal_required(row.get("Y_END"), rownum, "Y_End", row_errors)
        length = _parse_decimal_required(
            row.get("LENGTH"),
            rownum,
            "Length",
            row_errors,
            allow_blank_default=Decimal("0"),
        )

        if not row_errors:
            if not _in_lon_range(x_start):
                row_errors.append(f"Row {rownum}: X_Start must be between -180 and 180.")
            if not _in_lat_range(y_start):
                row_errors.append(f"Row {rownum}: Y_Start must be between -90 and 90.")
            if not _in_lon_range(x_end):
                row_errors.append(f"Row {rownum}: X_End must be between -180 and 180.")
            if not _in_lat_range(y_end):
                row_errors.append(f"Row {rownum}: Y_End must be between -90 and 90.")

        if row_errors:
            summary["skipped"] += 1
            summary["skipped_details"].append(f"Row {rownum}: skipped due to invalid coordinates/length.")
            summary["errors"].extend(row_errors)
            _report_progress(processed_rows)
            continue

        position = int(segment_position_counter.get(segment_code, 0)) + 1
        if position > 100:
            summary["skipped"] += 1
            summary["skipped_details"].append(
                f"Row {rownum}: skipped because segment {segment_obj.code} cannot exceed 100 subsegments."
            )
            summary["errors"].append(
                f"Row {rownum}: position {position} exceeds the max of 100 for segment {segment_obj.code}."
            )
            _report_progress(processed_rows)
            continue

        segment_position_counter[segment_code] = position
        subsegment_code = f"{segment_obj.code}-{position:02d}"
        pending.append(
            {
                "rownum": rownum,
                "code": subsegment_code,
                "detail": f"Row {rownum}: created subsegment {subsegment_code}.",
                "obj": SubSegment(
                    segment=segment_obj,
                    position=position,
                    code=subsegment_code,
                    start_lon=x_start,
                    start_lat=y_start,
                    end_lon=x_end,
                    end_lat=y_end,
                    distance=length,
                ),
            }
        )

        if len(pending) >= chunk_size:
            _flush_pending()
        _report_progress(processed_rows)

    _flush_pending()
    return summary
