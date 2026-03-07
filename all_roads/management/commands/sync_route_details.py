import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from all_roads.models import Route


class Command(BaseCommand):
    help = (
        "Parse lines that start with 'Route <code>:' from routes.html and sync the "
        "normalized text after ':' into Route.details."
    )

    ROUTE_LINE_RE = re.compile(r"^\s*Route\s+([A-Za-z0-9-]+)\s*:\s*(.*?)\s*$")

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(settings.BASE_DIR / "website" / "templates" / "website" / "routes.html"),
            help="Path to routes.html-like source file.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist updates to the database. Without this flag, command is dry-run.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).expanduser()
        if not source.exists():
            raise CommandError(f"Source file not found: {source}")

        extracted, duplicates = self._extract_route_details(source)
        if not extracted:
            raise CommandError("No valid 'Route <code>:' lines were found.")

        routes = Route.objects.filter(route__in=extracted.keys())
        db_by_code = {r.route: r for r in routes}

        missing_codes = sorted(set(extracted.keys()) - set(db_by_code.keys()))
        to_update = []
        unchanged = 0

        for code, details in extracted.items():
            obj = db_by_code.get(code)
            if not obj:
                continue
            if (obj.details or "") == details:
                unchanged += 1
                continue
            obj.details = details
            to_update.append(obj)

        self.stdout.write(self.style.NOTICE(f"Source: {source}"))
        self.stdout.write(f"Parsed route lines: {len(extracted)}")
        self.stdout.write(f"Duplicate route codes in source: {len(duplicates)}")
        self.stdout.write(f"Matched routes in DB: {len(db_by_code)}")
        self.stdout.write(f"Missing route codes in DB: {len(missing_codes)}")
        self.stdout.write(f"Will update: {len(to_update)}")
        self.stdout.write(f"Unchanged: {unchanged}")

        if missing_codes:
            sample = ", ".join(missing_codes[:15])
            suffix = " ..." if len(missing_codes) > 15 else ""
            self.stdout.write(self.style.WARNING(f"Missing codes sample: {sample}{suffix}"))

        if duplicates:
            sample = ", ".join(sorted(list(duplicates))[:15])
            suffix = " ..." if len(duplicates) > 15 else ""
            self.stdout.write(self.style.WARNING(f"Duplicate codes sample: {sample}{suffix}"))

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --apply to persist changes."))
            return

        with transaction.atomic():
            if to_update:
                Route.objects.bulk_update(to_update, ["details"])
        self.stdout.write(self.style.SUCCESS(f"Updated Route.details for {len(to_update)} route(s)."))

    def _extract_route_details(self, source: Path):
        extracted = {}
        duplicates = set()

        with source.open("r", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.rstrip("\n")
                match = self.ROUTE_LINE_RE.match(line)
                if not match:
                    continue

                code = match.group(1).strip()
                details = self._normalize_details(match.group(2))

                if code in extracted:
                    duplicates.add(code)
                extracted[code] = details

        return extracted, duplicates

    def _normalize_details(self, text: str) -> str:
        # Normalize unicode dashes/quotes and collapse whitespace.
        text = (
            text.replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2212", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .strip()
        )

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,;:.!?])", r"\1", text)
        text = re.sub(r"([(\[])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]])", r"\1", text)
        text = re.sub(r"\s*-\s*", " - ", text)

        # Remove trailing page-like integers left by OCR/table extraction.
        text = re.sub(r"\s+\d{1,4}$", "", text).strip()

        return text

