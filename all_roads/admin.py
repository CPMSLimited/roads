from django.contrib import admin
from .models import Road, Route, Segment, State, Address

# admin.site.register(Segment)
admin.site.register(Road)
admin.site.register(Route)
admin.site.register(Segment)
admin.site.register(State)
admin.site.register(Address)

class AddressAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
# admin.site.register(Address, AddressAdmin)
