from django import template

register = template.Library()

BUCKETS = {
    "good":        {"codes": ["00CC00"],                "canonical": "00CC00"},
    "tolerable":   {"codes": ["339933"],                "canonical": "339933"},
    "intolerable": {"codes": ["FF9966"],                "canonical": "FF9966"},
    "failed":      {"codes": ["FF5050"],                "canonical": "FF5050"},
    "no_response": {"codes": ["666699"],                "canonical": "666699"},
}

# ------------ generic hex helpers ------------
@register.filter
def norm_hex(value):
    if not value:
        return ""
    s = str(value).strip().lstrip("#")
    if len(s) == 3 and all(c in "0123456789abcdefABCDEF" for c in s):
        s = "".join(c*2 for c in s)
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        return s.lower()
    return ""

def _yiq_contrast(hex6: str) -> str:
    r = int(hex6[0:2], 16); g = int(hex6[2:4], 16); b = int(hex6[4:6], 16)
    yiq = (r*299 + g*587 + b*114) / 1000
    return "black" if yiq >= 128 else "white"

@register.filter
def text_contrast(value):
    hx = norm_hex(value)
    return _yiq_contrast(hx) if hx else "black"

# ------------ bucket logic ------------
def _bucket_for_hex(hx: str) -> str | None:
    n = norm_hex(hx)
    if not n:
        return None
    for name, data in BUCKETS.items():
        if n.upper() in [c.upper() for c in data["codes"]]:
            return name
    return None

@register.filter
def canonical_color(hex_value):
    """
    Given any status hex, return the canonical bucket colour hex (rrggbb).
    If it doesn't match any bucket, return normalized input (best effort).
    """
    b = _bucket_for_hex(hex_value)
    if b:
        return BUCKETS[b]["canonical"].lower()
    # fallback to given colour if valid
    return norm_hex(hex_value)

@register.filter
def bucket_color(bucket_name):
    """
    Given a bucket name ('good', 'tolerable', etc.), return its canonical hex.
    """
    info = BUCKETS.get(str(bucket_name).lower())
    return info["canonical"].lower() if info else ""
