ZONE_MAPPING = {
    "Inner West": ["Newtown", "Marrickville", "Leichhardt", "Annandale", "Glebe"],
    "Eastern Suburbs": ["Bondi", "Randwick", "Coogee", "Maroubra", "Paddington"],
    "CBD": ["Surry Hills", "Darlinghurst", "Potts Point", "Pyrmont"],
    "South Sydney": ["Alexandria", "Waterloo", "Redfern", "Mascot"],
    "Inner City": ["Rozelle", "Balmain"],
}

ZONES = list(ZONE_MAPPING.keys())

SUBURBS = [
    ("Surry Hills", "2010"), ("Bondi", "2026"), ("Newtown", "2042"),
    ("Paddington", "2021"), ("Glebe", "2037"), ("Marrickville", "2204"),
    ("Redfern", "2016"), ("Rozelle", "2039"), ("Balmain", "2041"),
    ("Pyrmont", "2009"), ("Alexandria", "2015"), ("Waterloo", "2017"),
    ("Darlinghurst", "2010"), ("Potts Point", "2011"), ("Randwick", "2031"),
    ("Coogee", "2034"), ("Maroubra", "2035"), ("Mascot", "2020"),
    ("Leichhardt", "2040"), ("Annandale", "2038"),
]

ORDER_STATUSES = ["pending", "allocated", "in_transit", "delivered", "failed"]
SERVICE_LEVELS = ["express", "standard", "economy"]
DRIVER_STATUSES = ["available", "on_route", "offline"]
VEHICLE_TYPES = ["Van", "Truck"]

STREET_NAMES = [
    "King", "Queen", "George", "Elizabeth", "Victoria",
    "Crown", "Oxford", "Park",
]

FIRST_NAMES = [
    "James", "Sarah", "Michael", "Emma", "David",
    "Olivia", "Daniel", "Sophie", "Matthew", "Isabella",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Davis", "Miller", "Wilson", "Moore", "Taylor",
]
