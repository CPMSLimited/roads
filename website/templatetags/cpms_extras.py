from django import template

register = template.Library()

@register.filter
def seconds_to_hhmm(value):
    """Convert seconds -> HH:MM (e.g., 3725 -> 01:02)."""
    try:
        total = int(value or 0)
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "00:00"

# If your backend stores status as a HEX colour, map it to a label.
# Update the hex keys below to match your get_status_color mapping.
STATUS_MAP = {
    "00aa00": ("Good", "badge-good"),
    "f0c000": ("Tolerable", "badge-tolerable"),
    "e67e22": ("Intolerable", "badge-intolerable"),
    "d9534f": ("Failed", "badge-failed"),
}
# Accept 'abc123' or '#abc123'
def _norm_hex(h):
    if not h: return ""
    h = str(h).lower().strip()
    return h.lstrip("#")

@register.filter
def status_label(hex_colour):
    return STATUS_MAP.get(_norm_hex(hex_colour), ("Unknown", "badge-unknown"))[0]

@register.filter
def status_class(hex_colour):
    return STATUS_MAP.get(_norm_hex(hex_colour), ("Unknown", "badge-unknown"))[1]
