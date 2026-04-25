from functools import lru_cache

from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError


DEFAULT_MOTORABILITY_SETTINGS = {
    "failed_max_speed": 40,
    "intolerable_min_speed": 40,
    "intolerable_max_speed": 60,
    "tolerable_min_speed": 60,
    "tolerable_max_speed": 80,
    "good_min_speed": 80,
}


@lru_cache(maxsize=1)
def _load_motorability_settings():
    if not apps.ready:
        return dict(DEFAULT_MOTORABILITY_SETTINGS)
    try:
        model = apps.get_model("all_roads", "MotorabilitySetting")
        instance = model.objects.order_by("id").first()
    except (LookupError, OperationalError, ProgrammingError):
        instance = None
    if not instance:
        return dict(DEFAULT_MOTORABILITY_SETTINGS)
    return {
        "failed_max_speed": int(instance.failed_max_speed),
        "intolerable_min_speed": int(instance.intolerable_min_speed),
        "intolerable_max_speed": int(instance.intolerable_max_speed),
        "tolerable_min_speed": int(instance.tolerable_min_speed),
        "tolerable_max_speed": int(instance.tolerable_max_speed),
        "good_min_speed": int(instance.good_min_speed),
    }


def clear_motorability_settings_cache():
    _load_motorability_settings.cache_clear()


def get_motorability_settings():
    return dict(_load_motorability_settings())


def get_status_color(speed: float) -> str:
    try:
        speed = float(speed or 0)
    except (TypeError, ValueError):
        speed = 0
    settings = get_motorability_settings()
    if speed <= 0:
        return "666699"
    if speed < settings["failed_max_speed"]:
        return "FF5050"
    if speed < settings["intolerable_max_speed"]:
        return "FF9966"
    if speed < settings["tolerable_max_speed"]:
        return "00CC00"
    return "05700B"
