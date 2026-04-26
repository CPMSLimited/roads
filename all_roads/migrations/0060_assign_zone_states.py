from django.db import migrations


ZONE_STATE_MAP = {
    "West": [
        "FCT",
        "Kogi",
        "Niger",
        "Kaduna",
        "Kano",
        "Katsina",
        "Kebbi",
        "Sokoto",
        "Zamfara",
        "Ekiti",
        "Kwara",
        "Oyo",
        "Osun",
        "Lagos I",
        "Lagos II",
        "Ogun",
        "Delta",
        "Edo",
        "Ondo",
    ],
    "East": [
        "Benue",
        "Plateau",
        "Taraba",
        "Nasarawa",
        "Yobe",
        "Borno",
        "Jigawa",
        "Adamawa",
        "Bauchi",
        "Gombe",
        "Anambra",
        "Enugu",
        "Imo",
        "Abia",
        "Ebonyi",
        "Cross River",
        "Akwa Ibom",
        "Bayelsa",
        "Rivers",
    ],
    "North-Central I": ["FCT", "Kogi", "Niger"],
    "North-West I": ["Kaduna", "Kano", "Katsina"],
    "North-West II": ["Kebbi", "Sokoto", "Zamfara"],
    "South-West I": ["Ekiti", "Kwara", "Oyo", "Osun"],
    "South-West II": ["Lagos I", "Lagos II", "Ogun"],
    "South-South II": ["Delta", "Edo", "Ondo"],
    "North-Central II": ["Benue", "Plateau", "Taraba", "Nasarawa"],
    "North-East I": ["Yobe", "Borno", "Jigawa"],
    "North-East II": ["Adamawa", "Bauchi", "Gombe"],
    "South-East I": ["Anambra", "Enugu", "Imo"],
    "South-East II": ["Abia", "Ebonyi", "Cross River"],
    "South-South I": ["Akwa Ibom", "Bayelsa", "Rivers"],
}


def get_or_create_state(State, state_name):
    existing = State.objects.filter(state__iexact=state_name).first()
    if existing:
        return existing
    return State.objects.create(state=state_name)


def assign_zone_states(apps, schema_editor):
    State = apps.get_model("all_roads", "State")
    Zone = apps.get_model("all_roads", "Zone")

    for zone_name, state_names in ZONE_STATE_MAP.items():
        zone, _ = Zone.objects.get_or_create(zone=zone_name)
        states = [get_or_create_state(State, state_name) for state_name in state_names]
        zone.states.set(states)


def unassign_zone_states(apps, schema_editor):
    Zone = apps.get_model("all_roads", "Zone")
    for zone_name in ZONE_STATE_MAP:
        try:
            zone = Zone.objects.get(zone=zone_name)
        except Zone.DoesNotExist:
            continue
        zone.states.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0059_add_zone"),
    ]

    operations = [
        migrations.RunPython(assign_zone_states, unassign_zone_states),
    ]
