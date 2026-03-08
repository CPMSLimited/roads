from rest_framework import serializers
from all_roads.models import Segment

class SegmentSerializer(serializers.ModelSerializer):
    settlement_type = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    carriages = serializers.IntegerField(min_value=1, max_value=9, required=False, allow_null=True)
    lanes = serializers.IntegerField(min_value=1, max_value=9, required=False, allow_null=True)
    pavement_type = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    junctions = serializers.IntegerField(min_value=1, max_value=9, required=False, allow_null=True)
    culverts = serializers.IntegerField(min_value=1, max_value=9, required=False, allow_null=True)
    bridges = serializers.IntegerField(min_value=1, max_value=9, required=False, allow_null=True)

    class Meta:
        model = Segment
        fields = '__all__'
