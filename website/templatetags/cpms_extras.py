from django import template

register = template.Library()

@register.filter
def norm_hex(value):
    """
    Normalise a hex string to 'rrggbb' (no leading '#').
    Returns '' if not usable.
    """
    if not value:
        return ""
    s = str(value).strip().lstrip("#")
    # Accept 3-char shorthand too (e.g., '0f3' -> '00ff33')
    if len(s) == 3 and all(c in "0123456789abcdefABCDEF" for c in s):
        s = "".join(c*2 for c in s)
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        return s.lower()
    return ""

def _yiq_contrast(hex6: str) -> str:
    """
    Return 'black' or 'white' for best contrast on the given background.
    Uses YIQ formula (good heuristic for legibility).
    """
    r = int(hex6[0:2], 16)
    g = int(hex6[2:4], 16)
    b = int(hex6[4:6], 16)
    yiq = (r*299 + g*587 + b*114) / 1000
    return "black" if yiq >= 128 else "white"

@register.filter
def text_contrast(value):
    """
    Given a hex background (with or without '#'), return 'black' or 'white'
    for readable foreground text.
    """
    hx = norm_hex(value)
    if not hx:
        return "black"  # safe default
    return _yiq_contrast(hx)
