# all_roads/services.py
from decimal import Decimal
import requests
from decouple import config
from all_roads.models import Segment, Address
from all_roads.utils import get_status_color

def get_or_create_address(address_str, lat, lng):
    return Address.objects.get_or_create(
        address=address_str,
        defaults={"lat": lat, "lng": lng}
    )[0]

def refresh_segments(codes=None, sleep_between=0.0):
    qs = Segment.objects.all()
    if codes:
        qs = qs.filter(code__in=codes)
    return refresh_segments_from_google(qs, sleep_between=sleep_between)

def refresh_segments_from_google(queryset, sleep_between=0.0):
    """
    Core updater: iterates queryset of Segment, calls Google Distance Matrix,
    updates distance/travel_time/avg_speed/status/start_point/end_point.
    Returns summary dict.
    """
    api_key = config("GOOGLE_ROUTES_API_KEY")
    updated, failed = 0, 0

    for segment in queryset.iterator(chunk_size=200):
        try:
            origin = f"{segment.start_lat},{segment.start_lon}"
            destination = f"{segment.end_lat},{segment.end_lon}"
            url = (
                "https://maps.googleapis.com/maps/api/distancematrix/json"
                f"?origins={origin}&destinations={destination}"
                f"&mode=driving&units=metric&key={api_key}"
            )

            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "OK":
                raise ValueError(f"Bad API status: {data.get('status')}")

            el = data["rows"][0]["elements"][0]
            if el.get("status") != "OK":
                raise ValueError(f"Element status: {el.get('status')}")

            dist_km = round(el["distance"]["value"] / 1000, 2)
            dur_s = int(el["duration"]["value"])
            speed = round(dist_km / (dur_s / 3600), 1) if dur_s > 0 else 0.0

            segment.distance = Decimal(str(dist_km))
            segment.travel_time = dur_s
            segment.avg_speed = Decimal(str(speed))
            segment.status = get_status_color(speed)
            segment.error_processing = False

            origin_addr = data["origin_addresses"][0]
            dest_addr = data["destination_addresses"][0]
            segment.start_point = get_or_create_address(origin_addr, segment.start_lat, segment.start_lon)
            segment.end_point   = get_or_create_address(dest_addr, segment.end_lat, segment.end_lon)

            segment.save()
            updated += 1

        except Exception as e:
            segment.error_processing = True
            segment.save(update_fields=["error_processing"])
            failed += 1

    return {"updated": updated, "failed": failed, "total": queryset.count()}

