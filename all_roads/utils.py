# Keep in one place so services, api, tasks can import without circulars
SPEED_COLOR_CODES = [
    (1, '666699'),          # No response / unusable data
    (40, 'FF5050'),         # Failed (<40 km/h)
    (60, 'FF9966'),         # Intolerable (40 to <60 km/h)
    (80, '00CC00'),         # Tolerable (60 to <80 km/h)
    (float('inf'), '05700B'),  # Good (>=80 km/h)
]

def get_status_color(speed: float) -> str:
    for threshold, color in SPEED_COLOR_CODES:
        if speed < threshold:
            return color
    return '666699'
