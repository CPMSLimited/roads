from rest_framework import serializers
from all_roads.models import Segment

class SegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segment
        fields = '__all__'