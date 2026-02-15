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

# Lat/lng coordinates for Sydney suburbs (for st.map display)
SUBURB_COORDS = {
    "Surry Hills": (-33.8833, 151.2111),
    "Bondi": (-33.8914, 151.2743),
    "Newtown": (-33.8976, 151.1792),
    "Paddington": (-33.8845, 151.2268),
    "Glebe": (-33.8794, 151.1862),
    "Marrickville": (-33.9117, 151.1553),
    "Redfern": (-33.8932, 151.2046),
    "Rozelle": (-33.8618, 151.1711),
    "Balmain": (-33.8581, 151.1794),
    "Pyrmont": (-33.8696, 151.1944),
    "Alexandria": (-33.9028, 151.2000),
    "Waterloo": (-33.9000, 151.2056),
    "Darlinghurst": (-33.8778, 151.2167),
    "Potts Point": (-33.8694, 151.2250),
    "Randwick": (-33.9139, 151.2417),
    "Coogee": (-33.9208, 151.2556),
    "Maroubra": (-33.9500, 151.2417),
    "Mascot": (-33.9275, 151.1933),
    "Leichhardt": (-33.8833, 151.1569),
    "Annandale": (-33.8822, 151.1700),
}

# Zone postcodes for settings
ZONE_POSTCODES = {
    "Inner West": "2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2204",
    "Eastern Suburbs": "2021, 2022, 2024, 2025, 2026, 2031, 2034, 2035",
    "CBD": "2000, 2009, 2010, 2011",
    "South Sydney": "2015, 2016, 2017, 2018, 2019, 2020",
    "Inner City": "2039, 2041",
}

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
