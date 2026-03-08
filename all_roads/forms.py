from django import forms

from .models import Segment


class SegmentForm(forms.ModelForm):
    class Meta:
        model = Segment
        fields = "__all__"
