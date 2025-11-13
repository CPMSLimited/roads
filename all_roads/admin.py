from django.contrib import admin
from .models import Road, Route, Segment, State, Address, SubSegment

# admin.site.register(Segment)
admin.site.register(Road)
admin.site.register(Route)
# admin.site.register(Segment)
admin.site.register(State)
admin.site.register(Address)

class AddressAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
# admin.site.register(Address, AddressAdmin)

@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ("code", "route", "state", "name", "avg_speed", "status")
    list_filter = ("route", "state", "status")
    search_fields = ("code", "name", "state", "route__route")  # <-- required for autocomplete

@admin.register(SubSegment)
class SubSegmentAdmin(admin.ModelAdmin):
    list_display = ("code", "segment", "position", "distance", "travel_time", "avg_speed", "status", "error_processing")
    list_filter = ("status", "error_processing", "segment__route")
    search_fields = ("code", "segment__code", "segment__name")
    autocomplete_fields = ("segment",)  # works now because SegmentAdmin has search_fields
    ordering = ("segment", "position")
