from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


def get_default_amina_bello_user_id():
    User = get_user_model()
    existing = (
        User.objects.filter(first_name__iexact="Amina", last_name__iexact="Bello")
        .order_by("id")
        .first()
    )
    if existing:
        return existing.pk

    username_field = getattr(User, "USERNAME_FIELD", "username")
    base_username = "amina.bello"
    username = base_username
    suffix = 1
    while User.objects.filter(**{username_field: username}).exists():
        suffix += 1
        username = f"{base_username}{suffix}"

    create_kwargs = {username_field: username}
    if getattr(User, "EMAIL_FIELD", ""):
        create_kwargs[User.EMAIL_FIELD] = f"{username}@example.com"

    manager = User.objects
    if hasattr(manager, "create_user"):
        user = manager.create_user(password=None, **create_kwargs)
    else:
        user = manager.create(**create_kwargs)
    user.first_name = "Amina"
    user.last_name = "Bello"
    if hasattr(user, "set_unusable_password"):
        user.set_unusable_password()
    user.save()
    return user.pk


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


class DefectType(models.Model):
    CODE_PAVEMENT = "pavement"
    CODE_SHOULDERS = "shoulders"
    CODE_DRAINAGE = "drainage"
    CODE_TRAFFIC_VOLUME = "traffic_volume"
    CODE_BRIDGES = "bridges"
    CODE_CULVERTS = "culverts"
    CODE_ROAD_JUNCTIONS = "road_junctions"
    CODE_OTHERS = "others"

    CODE_CHOICES = [
        (CODE_PAVEMENT, "Pavement"),
        (CODE_SHOULDERS, "Shoulders"),
        (CODE_DRAINAGE, "Drainage"),
        (CODE_TRAFFIC_VOLUME, "Traffic Volume"),
        (CODE_BRIDGES, "Bridges"),
        (CODE_CULVERTS, "Culverts"),
        (CODE_ROAD_JUNCTIONS, "Road Junctions"),
        (CODE_OTHERS, "Others"),
    ]

    code = models.CharField(max_length=32, unique=True, choices=CODE_CHOICES)
    label = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class Defect(models.Model):
    WORKFLOW_DRAFT = "draft"
    WORKFLOW_RCA = "rca"
    WORKFLOW_PHYSICAL = "physical_inspection"
    WORKFLOW_SOLUTION = "solution_design"
    WORKFLOW_REPAIR_ONGOING = "repair_ongoing"
    WORKFLOW_REPAIR_COMPLETE = "repair_complete"

    WORKFLOW_STATUS_CHOICES = [
        (WORKFLOW_DRAFT, "Draft"),
        (WORKFLOW_RCA, "RCA"),
        (WORKFLOW_PHYSICAL, "Physical Inspection"),
        (WORKFLOW_SOLUTION, "Solution Design"),
        (WORKFLOW_REPAIR_ONGOING, "Repair ongoing"),
        (WORKFLOW_REPAIR_COMPLETE, "Repair complete"),
    ]

    CONDITION_TOLERABLE = "tolerable"
    CONDITION_INTOLERABLE = "intolerable"
    CONDITION_BAD = "bad"
    CONDITION_FAILED = "failed"

    CONDITION_CHOICES = [
        (CONDITION_TOLERABLE, "Tolerable"),
        (CONDITION_INTOLERABLE, "Intolerable"),
        (CONDITION_FAILED, "Failed"),
        (CONDITION_BAD, "Bad"),
    ]

    subsegment = models.ForeignKey(
        SubSegment,
        on_delete=models.CASCADE,
        related_name="defects",
    )
    defect_ref = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=get_default_amina_bello_user_id,
        related_name="assigned_defects",
    )
    senior_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_defects",
    )
    workflow_status = models.CharField(
        max_length=32,
        choices=WORKFLOW_STATUS_CHOICES,
        default=WORKFLOW_DRAFT,
    )
    condition = models.CharField(
        max_length=24,
        choices=CONDITION_CHOICES,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-modified", "-id"]

    def __str__(self):
        return f"{self.defect_ref or self.subsegment.code} - {self.get_workflow_status_display()}"

    def save(self, *args, **kwargs):
        if not self.defect_ref and self.subsegment_id:
            self.defect_ref = self._generate_defect_ref()
        super().save(*args, **kwargs)

    def _generate_defect_ref(self):
        base_code = (self.subsegment.code or "SUBSEG").upper()
        date_part = timezone.now().strftime("%Y%m%d")
        prefix = f"{base_code}-{date_part}-"
        last_ref = (
            Defect.objects.filter(defect_ref__startswith=prefix)
            .order_by("-defect_ref")
            .values_list("defect_ref", flat=True)
            .first()
        )
        seq = 1
        if last_ref:
            try:
                seq = int(last_ref.rsplit("-", 1)[-1]) + 1
            except (TypeError, ValueError):
                seq = 1
        return f"{prefix}{seq:03d}"


class RootCauseAnalysis(models.Model):
    DESCRIPTION_PAVEMENT = "pavement"
    DESCRIPTION_SHOULDERS = "shoulders"
    DESCRIPTION_DRAINAGE = "drainage"
    DESCRIPTION_TRAFFIC_VOLUME = "traffic_volume"
    DESCRIPTION_BRIDGES = "bridges"
    DESCRIPTION_CULVERTS = "culverts"
    DESCRIPTION_ROAD_JUNCTIONS = "road_junctions"
    DESCRIPTION_OTHERS = "others"

    DESCRIPTION_CHOICES = [
        (DESCRIPTION_PAVEMENT, "Pavement"),
        (DESCRIPTION_SHOULDERS, "Shoulders"),
        (DESCRIPTION_DRAINAGE, "Drainage"),
        (DESCRIPTION_TRAFFIC_VOLUME, "Traffic Volume"),
        (DESCRIPTION_BRIDGES, "Bridges"),
        (DESCRIPTION_CULVERTS, "Culverts"),
        (DESCRIPTION_ROAD_JUNCTIONS, "Road Junctions"),
        (DESCRIPTION_OTHERS, "Others"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_COMPLETE = "complete"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_COMPLETE, "Complete"),
    ]

    subsegment = models.ForeignKey(
        SubSegment,
        on_delete=models.CASCADE,
        related_name="root_cause_analyses",
    )
    defect = models.ForeignKey(
        Defect,
        on_delete=models.CASCADE,
        related_name="root_cause_analyses",
        null=True,
        blank=True,
    )
    location = models.CharField(max_length=32)
    description = models.CharField(max_length=32, choices=DESCRIPTION_CHOICES)
    description_options = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    defect_types = models.ManyToManyField(
        DefectType,
        blank=True,
        related_name="root_cause_analyses",
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"RCA {self.subsegment.code} ({self.get_description_display()})"


class RootCauseDetail(models.Model):
    FEATURE_SUBGRADE_PROPERTIES = "subgrade_properties"
    FEATURE_VEGETATION = "vegetation"
    FEATURE_TOPOGRAPHY = "topography"
    FEATURE_DRAINAGE_CHARACTERISTICS = "drainage_characteristics"
    FEATURE_TEMPERATURE_HUMIDITY = "temperature_humidity"

    NATURAL_FEATURE_CHOICES = [
        (FEATURE_SUBGRADE_PROPERTIES, "Subgrade Properties"),
        (FEATURE_VEGETATION, "Vegetation"),
        (FEATURE_TOPOGRAPHY, "Topography"),
        (FEATURE_DRAINAGE_CHARACTERISTICS, "Drainage Characteristics"),
        (FEATURE_TEMPERATURE_HUMIDITY, "Temperature & Humidity"),
    ]

    CHARACTERISTIC_SUBGRADE_ALLUVIAL = "alluvial"
    CHARACTERISTIC_SUBGRADE_FOREST_CLAYEY = "forest_clayey"
    CHARACTERISTIC_SUBGRADE_LATERITIC = "lateritic"
    CHARACTERISTIC_SUBGRADE_SANDY = "sandy"

    CHARACTERISTIC_VEGETATION_MANGROVE = "mangrove_forest"
    CHARACTERISTIC_VEGETATION_RAIN_FOREST = "rain_forest"
    CHARACTERISTIC_VEGETATION_LIGHT_FOREST = "light_forest"
    CHARACTERISTIC_VEGETATION_SAVANNAH = "savannah"
    CHARACTERISTIC_VEGETATION_SAHEL = "sahel_savannah"

    CHARACTERISTIC_TOPO_HILL_TOP = "hill_top"
    CHARACTERISTIC_TOPO_STEEP = "steeply_sloping_gt_20"
    CHARACTERISTIC_TOPO_MODERATE = "moderately_sloping_10_to_20"
    CHARACTERISTIC_TOPO_MILD = "mildly_sloping_lt_10"
    CHARACTERISTIC_TOPO_FLAT = "flat"
    CHARACTERISTIC_TOPO_VALLEY = "valley"

    CHARACTERISTIC_DRAINAGE_SUBGRADE_DRAINAGE = "subgrade_drainage"
    CHARACTERISTIC_DRAINAGE_VEGETATION_COVER = "vegetation_cover"
    CHARACTERISTIC_DRAINAGE_TOPOGRAPHY = "topography"
    CHARACTERISTIC_DRAINAGE_RIVERS_STREAMS = "rivers_streams"

    CHARACTERISTIC_TEMP_VERY_HOT_VERY_DRY = "very_hot_very_dry"
    CHARACTERISTIC_TEMP_MOD_HOT_DRY = "moderately_hot_dry"
    CHARACTERISTIC_TEMP_MOD_HOT_HUMID = "moderately_hot_humid"
    CHARACTERISTIC_TEMP_COOL_DRY = "cool_dry"

    CHARACTERISTIC_CHOICES_BY_FEATURE = {
        FEATURE_SUBGRADE_PROPERTIES: [
            (CHARACTERISTIC_SUBGRADE_ALLUVIAL, "Alluvial"),
            (CHARACTERISTIC_SUBGRADE_FOREST_CLAYEY, "Forest/Clayey"),
            (CHARACTERISTIC_SUBGRADE_LATERITIC, "Lateritic"),
            (CHARACTERISTIC_SUBGRADE_SANDY, "Sandy"),
        ],
        FEATURE_VEGETATION: [
            (CHARACTERISTIC_VEGETATION_MANGROVE, "Mangrove Forest"),
            (CHARACTERISTIC_VEGETATION_RAIN_FOREST, "Rain Forest"),
            (CHARACTERISTIC_VEGETATION_LIGHT_FOREST, "Light Forest"),
            (CHARACTERISTIC_VEGETATION_SAVANNAH, "Savannah"),
            (CHARACTERISTIC_VEGETATION_SAHEL, "Sahel Savannah"),
        ],
        FEATURE_TOPOGRAPHY: [
            (CHARACTERISTIC_TOPO_HILL_TOP, "Hill Top"),
            (CHARACTERISTIC_TOPO_STEEP, "Steeply Sloping (> 20 deg)"),
            (CHARACTERISTIC_TOPO_MODERATE, "Moderately Sloping (10 < x < 20 deg)"),
            (CHARACTERISTIC_TOPO_MILD, "Mildly Sloping (x < 10 deg)"),
            (CHARACTERISTIC_TOPO_FLAT, "Flat"),
            (CHARACTERISTIC_TOPO_VALLEY, "Valley"),
        ],
        FEATURE_DRAINAGE_CHARACTERISTICS: [
            (CHARACTERISTIC_DRAINAGE_SUBGRADE_DRAINAGE, "Subgrade Drainage"),
            (CHARACTERISTIC_DRAINAGE_VEGETATION_COVER, "Vegetation Cover"),
            (CHARACTERISTIC_DRAINAGE_TOPOGRAPHY, "Topography"),
            (CHARACTERISTIC_DRAINAGE_RIVERS_STREAMS, "River and Streams"),
        ],
        FEATURE_TEMPERATURE_HUMIDITY: [
            (CHARACTERISTIC_TEMP_VERY_HOT_VERY_DRY, "Very Hot & Very Dry"),
            (CHARACTERISTIC_TEMP_MOD_HOT_DRY, "Moderately Hot & Dry"),
            (CHARACTERISTIC_TEMP_MOD_HOT_HUMID, "Moderately Hot & Humid"),
            (CHARACTERISTIC_TEMP_COOL_DRY, "Cool & Dry"),
        ],
    }

    CHARACTERISTIC_CHOICES = [
        choice
        for choices in CHARACTERISTIC_CHOICES_BY_FEATURE.values()
        for choice in choices
    ]

    root_cause_analysis = models.ForeignKey(
        RootCauseAnalysis,
        on_delete=models.CASCADE,
        related_name="root_cause_details",
    )
    natural_feature = models.CharField(max_length=40, choices=NATURAL_FEATURE_CHOICES)
    characteristic = models.CharField(max_length=40, choices=CHARACTERISTIC_CHOICES)
    root_cause_analysis_text = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["root_cause_analysis", "natural_feature"],
                name="uq_rootcausedetail_analysis_feature",
            ),
        ]

    def __str__(self):
        return (
            f"{self.root_cause_analysis.subsegment.code} - "
            f"{self.get_natural_feature_display()}: {self.get_characteristic_display()}"
        )

    def clean(self):
        super().clean()
        valid_values = {
            value
            for value, _ in self.CHARACTERISTIC_CHOICES_BY_FEATURE.get(
                self.natural_feature, []
            )
        }
        if self.characteristic and self.characteristic not in valid_values:
            raise ValidationError(
                {"characteristic": "Characteristic does not match the selected natural feature."}
            )


class PhysicalInspection(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_COMPLETE = "complete"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_COMPLETE, "Complete"),
    ]

    subsegment = models.ForeignKey(
        SubSegment,
        on_delete=models.CASCADE,
        related_name="physical_inspections",
    )
    defect = models.ForeignKey(
        Defect,
        on_delete=models.CASCADE,
        related_name="physical_inspections",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    defect_types = models.ManyToManyField(
        DefectType,
        blank=True,
        related_name="physical_inspections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Physical Inspection {self.subsegment.code}"


class PhysicalInspectionAnalysis(models.Model):
    CONSIDERATION_DESIGN = "design"
    CONSIDERATION_CONSTRUCTION = "construction"
    CONSIDERATION_USAGE = "usage"
    CONSIDERATION_CHOICES = [
        (CONSIDERATION_DESIGN, "Design Considerations"),
        (CONSIDERATION_CONSTRUCTION, "Construction Considerations"),
        (CONSIDERATION_USAGE, "Usage Considerations"),
    ]

    OPTION_HORIZONTAL_ALIGNMENT = "horizontal_alignment"
    OPTION_VERTICAL_ALIGNMENT = "vertical_alignment"
    OPTION_CARRIAGE_WAY_CROSS_SECTIONS = "carriage_way_cross_sections"
    OPTION_BRIDGES = "bridges"
    OPTION_CULVERTS = "culverts"
    OPTION_ROAD_JUNCTION = "road_junction"
    OPTION_DESIGN_SPEED = "design_speed"
    OPTION_DESIGN_AXLE_LOAD = "design_axle_load"
    OPTION_PAVEMENT_BASE_SUBBASE_FAILURE = "pavement_base_subbase_failure"
    OPTION_DRAINAGE_CONSTRUCTION_FAILURE = "drainage_construction_failure"
    OPTION_PAVEMENT_FAILURE = "pavement_failure"
    OPTION_DRAINAGE_FAILURE = "drainage_failure"
    OPTION_ENCROACHMENT = "encroachment"

    OPTION_CHOICES = [
        (OPTION_HORIZONTAL_ALIGNMENT, "Horizontal Alignment"),
        (OPTION_VERTICAL_ALIGNMENT, "Vertical Alignment"),
        (OPTION_CARRIAGE_WAY_CROSS_SECTIONS, "Carriage Way Cross-Sections"),
        (OPTION_BRIDGES, "Bridges"),
        (OPTION_CULVERTS, "Culverts"),
        (OPTION_ROAD_JUNCTION, "Road Junction"),
        (OPTION_DESIGN_SPEED, "Design Speed"),
        (OPTION_DESIGN_AXLE_LOAD, "Design Axle Load"),
        (OPTION_PAVEMENT_BASE_SUBBASE_FAILURE, "Pavement, Base and Sub-base Failure"),
        (OPTION_DRAINAGE_CONSTRUCTION_FAILURE, "Drainage Construction Failure"),
        (OPTION_PAVEMENT_FAILURE, "Pavement Failure"),
        (OPTION_DRAINAGE_FAILURE, "Drainage Failure"),
        (OPTION_ENCROACHMENT, "Encroachment"),
    ]

    OPTIONS_BY_CONSIDERATION = {
        CONSIDERATION_DESIGN: {
            OPTION_HORIZONTAL_ALIGNMENT,
            OPTION_VERTICAL_ALIGNMENT,
            OPTION_CARRIAGE_WAY_CROSS_SECTIONS,
            OPTION_BRIDGES,
            OPTION_CULVERTS,
            OPTION_ROAD_JUNCTION,
            OPTION_DESIGN_SPEED,
            OPTION_DESIGN_AXLE_LOAD,
        },
        CONSIDERATION_CONSTRUCTION: {
            OPTION_PAVEMENT_BASE_SUBBASE_FAILURE,
            OPTION_DRAINAGE_CONSTRUCTION_FAILURE,
        },
        CONSIDERATION_USAGE: {
            OPTION_PAVEMENT_FAILURE,
            OPTION_DRAINAGE_FAILURE,
            OPTION_ENCROACHMENT,
        },
    }

    inspection = models.ForeignKey(
        PhysicalInspection,
        on_delete=models.CASCADE,
        related_name="analysis_rows",
    )
    consideration_type = models.CharField(max_length=24, choices=CONSIDERATION_CHOICES)
    option = models.CharField(max_length=64, choices=OPTION_CHOICES)
    option_description = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "option"],
                name="uq_physicalinspection_option",
            ),
        ]

    def __str__(self):
        return (
            f"{self.inspection.subsegment.code} - "
            f"{self.get_consideration_type_display()} - {self.get_option_display()}"
        )

    def clean(self):
        super().clean()
        valid_options = self.OPTIONS_BY_CONSIDERATION.get(self.consideration_type, set())
        if self.option and self.option not in valid_options:
            raise ValidationError(
                {"option": "Option does not match the selected consideration type."}
            )


class PhysicalInspectionCharacteristic(models.Model):
    CHARACTERISTICS_BY_OPTION = {
        PhysicalInspectionAnalysis.OPTION_HORIZONTAL_ALIGNMENT: [
            "Straight",
            "Gentle Curve",
            "Sharp Bend",
            "Road Junction",
        ],
        PhysicalInspectionAnalysis.OPTION_VERTICAL_ALIGNMENT: [
            "Hill Top",
            "Steeply Sloping (x>20o)",
            "Moderate Sloping (10<x<20o)",
            "Mildly Sloping (x<10o)",
            "Flat",
            "Valley",
        ],
        PhysicalInspectionAnalysis.OPTION_CARRIAGE_WAY_CROSS_SECTIONS: [
            "No of Carriage Ways",
            "No of Lanes",
            "Width of Lanes",
            "Width of Shoulders",
            "Pavement Type",
            "Pavement Specifications",
            "Side Drains",
            "Median Type",
            "Adjacent Land-Use",
        ],
        PhysicalInspectionAnalysis.OPTION_BRIDGES: [
            "Bridge Type",
            "Bridge Length",
            "No of Spans",
            "Bridge Width",
            "No of Carriage Ways",
        ],
        PhysicalInspectionAnalysis.OPTION_CULVERTS: [
            "Culvert Type",
            "Culvert Length",
            "No of Spans",
            "Culvert Width",
            "No of Carriage Ways",
        ],
        PhysicalInspectionAnalysis.OPTION_ROAD_JUNCTION: [
            "Junction Type",
            "Bridge Length",
            "No of Spans",
            "No of Carriage Ways",
        ],
        PhysicalInspectionAnalysis.OPTION_DESIGN_SPEED: ["Design Speed"],
        PhysicalInspectionAnalysis.OPTION_DESIGN_AXLE_LOAD: ["Design Axle Load"],
        PhysicalInspectionAnalysis.OPTION_PAVEMENT_BASE_SUBBASE_FAILURE: [
            "Materials Spec",
            "Layer Compaction",
            "Layer Thickness",
        ],
        PhysicalInspectionAnalysis.OPTION_DRAINAGE_CONSTRUCTION_FAILURE: [
            "Side Drains Capacity",
            "Side Drains Slope",
            "Side Drains Height",
            "Vertical Alignment",
            "Porous Pavement",
        ],
        PhysicalInspectionAnalysis.OPTION_PAVEMENT_FAILURE: [
            "Pavement Cracks",
            "Pavement Depressions",
            "Pavement Wearing",
        ],
        PhysicalInspectionAnalysis.OPTION_DRAINAGE_FAILURE: [
            "Side Drains Blockage",
            "Pavement Ponding",
            "Flooding",
            "Ground Saturation",
            "Blocked Culverts",
            "Siltation",
        ],
        PhysicalInspectionAnalysis.OPTION_ENCROACHMENT: [
            "Encroachment Type",
            "Infrastructure Installation",
        ],
    }

    analysis = models.ForeignKey(
        PhysicalInspectionAnalysis,
        on_delete=models.CASCADE,
        related_name="characteristics",
    )
    characteristic = models.CharField(max_length=64)
    value = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    row_index = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="For repeated carriage-way rows; keep between 1 and 8.",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.analysis.get_option_display()} - {self.characteristic}"

    def clean(self):
        super().clean()
        allowed = set(self.CHARACTERISTICS_BY_OPTION.get(self.analysis.option, []))
        if self.characteristic and self.characteristic not in allowed:
            raise ValidationError(
                {"characteristic": "Characteristic does not match the selected option."}
            )
        if (
            self.analysis.option == PhysicalInspectionAnalysis.OPTION_CARRIAGE_WAY_CROSS_SECTIONS
            and self.row_index is None
        ):
            raise ValidationError(
                {"row_index": "Row index is required for carriage-way cross-sections."}
            )
        if (
            self.analysis.option != PhysicalInspectionAnalysis.OPTION_CARRIAGE_WAY_CROSS_SECTIONS
            and self.row_index is not None
        ):
            raise ValidationError(
                {"row_index": "Row index is only allowed for carriage-way cross-sections."}
            )


class Library(models.Model):
    TYPE_TECHNICAL_GUIDE = "technical_guide"
    TYPE_USER_GUIDE = "user_guide"
    TYPE_ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    TYPE_PHYSICAL_INSPECTION = "physical_inspection"
    TYPE_SOLUTION_DESIGN = "solution_design"

    TYPE_CHOICES = [
        (TYPE_TECHNICAL_GUIDE, "Technical Guide"),
        (TYPE_USER_GUIDE, "User Guide"),
        (TYPE_ROOT_CAUSE_ANALYSIS, "Root Cause Analysis"),
        (TYPE_PHYSICAL_INSPECTION, "Physical Inspection"),
        (TYPE_SOLUTION_DESIGN, "Solution Design"),
    ]

    FILE_TYPE_DOCUMENT = "document"
    FILE_TYPE_SPREADSHEET = "spreadsheet"
    FILE_TYPE_PDF = "pdf"
    FILE_TYPE_CSV = "csv"
    FILE_TYPE_IMAGE = "image"
    FILE_TYPE_PRESENTATION = "presentation"
    FILE_TYPE_GEO_DATA = "geo_data"
    FILE_TYPE_OTHER = "other"

    FILE_TYPE_CHOICES = [
        (FILE_TYPE_DOCUMENT, "Document"),
        (FILE_TYPE_SPREADSHEET, "Spreadsheet"),
        (FILE_TYPE_PDF, "PDF"),
        (FILE_TYPE_CSV, "CSV"),
        (FILE_TYPE_IMAGE, "Image"),
        (FILE_TYPE_PRESENTATION, "Presentation"),
        (FILE_TYPE_GEO_DATA, "Geo Data"),
        (FILE_TYPE_OTHER, "Other"),
    ]

    entry_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    name = models.CharField(max_length=128)
    file = models.FileField(upload_to="library/files/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_library_files",
    )
    defect = models.ForeignKey(
        "Defect",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_files",
    )
    root_cause_analysis = models.ForeignKey(
        "RootCauseAnalysis",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_files",
    )
    physical_inspection = models.ForeignKey(
        "PhysicalInspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_files",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created", "-id"]

    def __str__(self):
        return f"{self.name} ({self.get_entry_type_display()})"
