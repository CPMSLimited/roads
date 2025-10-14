# views.py
import requests
from django.conf import settings
from django.http import JsonResponse
from all_roads.models import Segment
from decouple import config

def update_segment_distances(request):
    api_key = config('GOOGLE_ROUTES_API_KEY')

    segments = Segment.objects.all()
    updated = 0
    failed = 0

    for segment in segments:
        origin = f"{segment.start_lat},{segment.start_lon}"
        destination = f"{segment.end_lat},{segment.end_lon}"

        url = (
            "https://maps.googleapis.com/maps/api/distancematrix/json"
            f"?origins={origin}&destinations={destination}"
            f"&mode=driving&units=metric&key={api_key}"
        )

        try:
            response = requests.get(url)
            data = response.json()

            if data['status'] == 'OK':
                element = data['rows'][0]['elements'][0]

                if element['status'] == 'OK':
                    distance_meters = element['distance']['value']
                    duration_seconds = element['duration']['value']

                    segment.distance = round(distance_meters / 1000, 2)  # in km
                    segment.travel_time = duration_seconds  # in seconds

                    # Avoid division by zero
                    if duration_seconds > 0:
                        hours = duration_seconds / 3600
                        speed = distance_meters / 1000 / hours
                        segment.avg_speed = round(speed, 1)
                    else:
                        segment.avg_speed = 0.0

                    segment.save()
                    updated += 1
                else:
                    failed += 1
                    print(f"Element error: {element['status']} for segment {segment.code}")
            else:
                failed += 1
                print(f"API error: {data['status']}")

        except Exception as e:
            failed += 1
            print(f"Error processing segment {segment.code}: {e}")

    return JsonResponse({
        'updated': updated,
        'failed': failed,
        'total': segments.count()
    })
