# Keep in one place so services, api, tasks can import without circulars
SPEED_COLOR_CODES = [
    (1, '666699'),   # No response / very slow
    (40, 'FF0000'),  # Werser
    (50, 'FF5050'),  # Bad
    (60, 'FF9966'),  # Poor
    (70, 'FFFFCC'),  # Manage
    (80, '00CC00'),  # Ok
    (90, '339933'),  # Good
    (float('inf'), '006600'),  # Better
]

def get_status_color(speed: float) -> str:
    for threshold, color in SPEED_COLOR_CODES:
        if speed < threshold:
            return color
    return '666699'
