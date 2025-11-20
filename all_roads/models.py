from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
class State(models.Model):
    state = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.state

class Address(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=256, unique=True)
    name = models.CharField(max_length=30, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=5, default=0.0)
    lng = models.DecimalField(max_digits=9, decimal_places=5, default=0.0)

    def __str__(self):
        return self.name

class Segment(models.Model):
    STATUS_CHOICES = [
        ('666699', 'No response'),
        ('FF0000', 'Werser (<40 km/h)'),
        ('FF5050', 'Bad (<50 km/h)'),
        ('FF9966', 'Poor (<60 km/h)'),
        ('FFFFCC', 'Manageable (<70 km/h)'),
        ('00CC00', 'OK (<80 km/h)'),
        ('339933', 'Good (<90 km/h)'),
        ('006600', 'Better (>=90 km/h)'),
    ]

    route = models.ForeignKey(Route, db_column='route', on_delete=models.PROTECT, default=1)
    index = models.CharField(max_length=2, blank=True)
    name = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=30, blank=True)
    code = models.CharField(max_length=10, unique=True)
    start_lat = models.DecimalField(max_digits=9, decimal_places=5, default=0.00)
    start_lon = models.DecimalField(max_digits=9, decimal_places=5, default=0.00)
    end_lat = models.DecimalField(max_digits=9, decimal_places=5, default=0.00)
    end_lon = models.DecimalField(max_digits=9, decimal_places=5, default=0.00)
    start_point = models.ForeignKey(Address, related_name='start_point', on_delete=models.PROTECT, default=1)
    end_point = models.ForeignKey(Address, related_name='end_point', on_delete=models.PROTECT, default=1)
    map = models.ImageField(upload_to='images', blank=True)
    distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    travel_time = models.IntegerField(default=0)
    avg_speed = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    # direction
    error_processing = models.BooleanField(default=False)
    status = models.CharField(max_length=6, choices=STATUS_CHOICES, default='666699',
        help_text="Traffic color code based on average speed")

    def __str__(self):
        return self.code
    
class SubSegment(models.Model):
    """
    A sub-division of a Segment (typically 25 per Segment).
    SubSegments inherit most properties of Segment, but deliberately
    exclude: index, name, state, start_point, end_point.
    """
    segment = models.ForeignKey( Segment, on_delete=models.CASCADE,related_name="subsegments", db_index=True,)
    code = models.CharField(max_length=16, unique=True, blank=True)
    position = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(25)],
        help_text="Order of this sub-segment within its parent segment (1–25)."
    )
    start_lat = models.DecimalField(max_digits=18, decimal_places=16, default=0.00)
    start_lon = models.DecimalField(max_digits=18, decimal_places=16, default=0.00)
    end_lat   = models.DecimalField(max_digits=18, decimal_places=16, default=0.00)
    end_lon   = models.DecimalField(max_digits=18, decimal_places=16, default=0.00)
    distance    = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    travel_time = models.IntegerField(default=0)  # seconds
    avg_speed   = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)
    error_processing = models.BooleanField(default=False)
    status = models.CharField(
        max_length=6,
        choices=Segment.STATUS_CHOICES,
        default='666699',
        help_text="Traffic color code based on average speed"
    )

    class Meta:
        db_table = "sub_segments"
        verbose_name = "Sub-segment"
        verbose_name_plural = "Sub-segments"
        # Prevent duplicate positions within the same parent segment
        constraints = [
            models.UniqueConstraint(
                fields=["segment", "position"],
                name="uq_subsegment_segment_position"
            ),
            models.CheckConstraint(
                check=models.Q(position__gte=1) & models.Q(position__lte=25),
                name="ck_subsegment_position_1_25",
            ),
        ]
        ordering = ["segment_id", "position"]

    def __str__(self):
        return self.code or f"{self.segment.code}-{self.position:02d}"

    def save(self, *args, **kwargs):
        self._trim_coordinate_fields()
        if not self.code and self.segment_id and self.position:
            self.code = f"{self.segment.code}-{self.position:02d}"
        super().save(*args, **kwargs)

    @property
    def route(self):
        """Convenience: a sub-segment's route is the parent's route."""
        return self.segment.route

    def _trim_coordinate_fields(self):
        """
        Remove trailing zeros from the coordinate decimals before saving
        so that their string representation stays compact.
        """
        for field_name in ("start_lat", "start_lon", "end_lat", "end_lon"):
            value = getattr(self, field_name)
            if value is None:
                continue
            normalized = self._trim_decimal(value)
            setattr(self, field_name, normalized)

    @staticmethod
    def _trim_decimal(value):
        """
        Convert Decimal to a normalized representation without trailing zeros.
        """
        value = Decimal(value)
        as_str = format(value, "f")
        if "." in as_str:
            as_str = as_str.rstrip("0").rstrip(".")
        if as_str in {"", "-", "-0"}:
            as_str = "0"
        return Decimal(as_str)
