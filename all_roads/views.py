from django.shortcuts import render
from all_roads.models import Segment

def segment_list(request):
    segments = Segment.objects.all()
    return render(request, 'all_roads/segment_list.html', {'segments': segments})
