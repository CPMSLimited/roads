from django.db import models

class Road(models.Model):
    road = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return self.road

class Route(models.Model):
    road = models.ForeignKey(Road, db_column='road', on_delete=models.CASCADE)
    route = models.CharField(max_length=10, unique=True)
    index = models.CharField(max_length=2, blank=True)

    def __str__(self):
        return self.route

class Address(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=256, unique=True)
    name = models.CharField(max_length=30, blank=True)
    lat = models.DecimalField(max_digits=30, decimal_places=15, default=0.0)
    lng = models.DecimalField(max_digits=30, decimal_places=15, default=0.0)

    def __str__(self):
        return self.name
    
class Segment(models.Model):
    route = models.ForeignKey(Route, db_column='route', on_delete=models.PROTECT, default=1)
    index = models.CharField(max_length=2, blank=True)
    name = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=30, blank=True)
    code = models.CharField(max_length=10, unique=True)
    # start_point = models.ForeignKey(Address, related_name='start_point', on_delete=models.PROTECT, default=1) # id 1330 is No address
    # end_point = models.ForeignKey(Address, related_name='end_point', on_delete=models.PROTECT, default=1)
    map = models.ImageField(upload_to='images', blank=True)
    distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    travel_time = models.IntegerField(default=0)
    avg_speed = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    # direction
    status = models.CharField(max_length=6, default='F0F0F0')

    def __str__(self):
        return self.code