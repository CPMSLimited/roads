import uuid
from celery.result import AsyncResult

from all_roads.models import Segment
from all_roads.tasks import refresh_segments_task
from .serializers import SegmentSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status


@api_view(["GET"])
@permission_classes([AllowAny])  # tighten later
def task_status(request, task_id: uuid.UUID):
    """
    Returns Celery task status (and result/error if available).
    Handles UUID vs str issues and avoids 500 HTML pages.
    """
    try:
        tid = str(task_id)  # ensure string for Celery
        res = AsyncResult(tid)
        payload = {"task_id": tid, "state": res.state}
        if res.successful():
            payload["result"] = res.result
        elif res.failed():
            payload["error"] = str(res.result)
        elif isinstance(res.info, dict):
            payload["meta"] = res.info
        return Response(payload)
    except Exception as e:
        return Response(
            {"task_id": str(task_id), "state": "UNKNOWN", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([AllowAny])  # tighten as you like
def queue_refresh(request):
    """
    Body (JSON): { "codes": ["F100LAS1", "F102RIV2", ...] } (optional)
    Returns:     { "task_id": "..." }
    """
    codes = request.data.get("codes", None)

    # Validate if provided
    if codes is not None:
        if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
            return Response(
                {"detail": "codes must be a list of strings"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    async_result = refresh_segments_task.delay(codes=codes)
    return Response({"task_id": async_result.id}, status=status.HTTP_200_OK)

@api_view(['GET'])
def all_segments_view(request):
    segments = Segment.objects.all()
    serializer = SegmentSerializer(segments, many=True)
    return Response(serializer.data)
    
# ['Lagos','Bayelsa','Akwa ibom','Imo','Abia','Cross River','Anambra','Imo','Ebonyi','Cross River','Osun','Ekiti','Ondo','Nasarawa','Kwara','Niger','Kebbi','Ogun','Anambra','Rivers','Imo','Taraba','Kaduna','Borno','Kogi','Jigawa','Bauchi','Kano','Sokoto','Zamfara','Katsina','Benue','Delta','Edo','Imo','Oyo','Plateau','Gombe','Adamawa','Yobe']
