import requests
from django.http import JsonResponse
from all_roads.models import Segment, Address, Route, Road
from .serializers import SegmentSerializer
from decouple import config
from rest_framework.decorators import api_view
from rest_framework.response import Response
import time
from celery.result import AsyncResult
from all_roads.tasks import refresh_segments_task
from all_roads.utils import get_status_color

def get_or_create_address(address_str, lat, lng):
    return Address.objects.get_or_create(
        address=address_str,
        defaults={'lat': lat, 'lng': lng}
    )[0]

@api_view(["POST"])
def queue_update_segments(request):
    """
    Body (JSON): { "codes": ["F100LAS1", "F102RIV2", ...] }  (optional)
    Returns: { "task_id": "..." }
    """
    codes = request.data.get("codes")
    async_result = refresh_segments_task.delay(codes)
    return Response({"task_id": async_result.id})

@api_view(["GET"])
def task_status(request, task_id: str):
    """
    Returns Celery task status, and result if finished.
    """
    res = AsyncResult(task_id)
    payload = {"task_id": task_id, "state": res.state}
    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)
    return Response(payload)

def update_segment_distances(request):
    api_key = config('GOOGLE_ROUTES_API_KEY')
    segments = Segment.objects.all()

    updated, failed = 0, 0

    for segment in segments:
        time.sleep(1.0)
        try:
            origin = f"{segment.start_lat},{segment.start_lon}"
            destination = f"{segment.end_lat},{segment.end_lon}"

            url = (
                "https://maps.googleapis.com/maps/api/distancematrix/json"
                f"?origins={origin}&destinations={destination}"
                f"&mode=driving&units=metric&key={api_key}"
            )

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['status'] != 'OK':
                raise ValueError(f"Bad API status: {data['status']}")

            element = data['rows'][0]['elements'][0]
            if element['status'] != 'OK':
                raise ValueError(f"Element status not OK: {element['status']}")

            # Extract values
            distance_km = round(element['distance']['value'] / 1000, 2)
            duration_sec = element['duration']['value']
            speed = (distance_km / (duration_sec / 3600)) if duration_sec > 0 else 0.0

            # Update Segment
            segment.distance = distance_km
            segment.travel_time = duration_sec
            segment.avg_speed = round(speed, 1)
            segment.status = get_status_color(speed)
            segment.error_processing = False

            # Update Address references
            origin_address_str = data['origin_addresses'][0]
            destination_address_str = data['destination_addresses'][0]

            segment.start_point = get_or_create_address(origin_address_str, segment.start_lat, segment.start_lon)
            segment.end_point = get_or_create_address(destination_address_str, segment.end_lat, segment.end_lon)

            segment.save()
            updated += 1

        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            segment.error_processing = True
            segment.save(update_fields=['error_processing'])
            failed += 1
            print(f"[ERROR] Segment {segment.code}: {e}")

    return JsonResponse({
        'updated': updated,
        'failed': failed,
        'total': segments.count()
    })

@api_view(['GET'])
def all_segments_view(request):
    segments = Segment.objects.all()
    serializer = SegmentSerializer(segments, many=True)
    return Response(serializer.data)
    
# ['Lagos','Bayelsa','Akwa ibom','Imo','Abia','Cross River','Anambra','Imo','Ebonyi','Cross River','Osun','Ekiti','Ondo','Nasarawa','Kwara','Niger','Kebbi','Ogun','Anambra','Rivers','Imo','Taraba','Kaduna','Borno','Kogi','Jigawa','Bauchi','Kano','Sokoto','Zamfara','Katsina','Benue','Delta','Edo','Imo','Oyo','Plateau','Gombe','Adamawa','Yobe']