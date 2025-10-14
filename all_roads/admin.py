from django.contrib import admin
from .models import Road, Route
# from .models import Segment, Route#, Address

# admin.site.register(Segment)
admin.site.register(Road)
admin.site.register(Route)

class AddressAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
# admin.site.register(Address, AddressAdmin)
