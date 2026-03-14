# Keep in one place so services, api, tasks can import without circulars
SPEED_COLOR_CODES = [
    (1, '666699'),          # No response / unusable data
    (60, 'F70202'),         # Failed (<60 km/h)
    (70, 'FF8D28'),         # Intolerable (60 to <70 km/h)
    (80, '2A6FDD'),         # Tolerable (70 to <80 km/h)
    (float('inf'), '1F8A70'),  # Good (>=80 km/h)
]

def get_status_color(speed: float) -> str:
    for threshold, color in SPEED_COLOR_CODES:
        if speed < threshold:
            return color
    return '666699'
