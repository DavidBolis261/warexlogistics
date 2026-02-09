import pandas as pd
import random
from datetime import datetime, timedelta

from config.constants import (
    SUBURBS, FIRST_NAMES, LAST_NAMES, STREET_NAMES,
    ORDER_STATUSES, SERVICE_LEVELS,
)


def generate_mock_orders(n=50):
    statuses = ORDER_STATUSES
    status_weights = [0.15, 0.20, 0.30, 0.30, 0.05]
    service_weights = [0.2, 0.6, 0.2]

    orders = []
    base_time = datetime.now() - timedelta(hours=8)

    for i in range(n):
        suburb, postcode = random.choice(SUBURBS)
        status = random.choices(statuses, weights=status_weights)[0]
        service = random.choices(SERVICE_LEVELS, weights=service_weights)[0]
        order_time = base_time + timedelta(minutes=random.randint(0, 480))

        orders.append({
            "order_id": f"SMC-{random.randint(10000, 99999)}",
            "customer": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "address": f"{random.randint(1, 200)} {random.choice(STREET_NAMES)} St",
            "suburb": suburb,
            "postcode": postcode,
            "status": status,
            "service_level": service,
            "parcels": random.randint(1, 5),
            "created_at": order_time,
            "driver_id": f"DRV-{random.randint(100, 110)}" if status in ["allocated", "in_transit", "delivered"] else None,
            "eta": (order_time + timedelta(hours=random.randint(1, 4))).strftime("%H:%M") if status in ["allocated", "in_transit"] else None,
        })

    return pd.DataFrame(orders)


def generate_mock_drivers(n=10):
    names = [
        "Marcus Chen", "Sarah Thompson", "Ahmed Hassan", "Lisa Nguyen",
        "James Wilson", "Maria Garcia", "David Kim", "Emma Roberts",
        "Ryan O'Brien", "Priya Patel",
    ]
    vehicles = ["Van", "Truck", "Van", "Van", "Truck", "Van", "Van", "Truck", "Van", "Van"]
    plates = [
        f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}-{random.randint(100, 999)}"
        for _ in range(n)
    ]
    statuses = ["available", "on_route", "on_route", "on_route", "available", "on_route", "offline", "on_route", "available", "on_route"]

    drivers = []
    for i in range(n):
        drivers.append({
            "driver_id": f"DRV-{100 + i}",
            "name": names[i],
            "vehicle_type": vehicles[i],
            "plate": plates[i],
            "status": statuses[i],
            "current_zone": random.choice(["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"]),
            "deliveries_today": random.randint(8, 25),
            "success_rate": round(random.uniform(0.94, 0.99), 2),
            "rating": round(random.uniform(4.5, 5.0), 1),
            "active_orders": random.randint(0, 8) if statuses[i] == "on_route" else 0,
            "phone": f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}",
        })

    return pd.DataFrame(drivers)


def generate_mock_runs(n=15):
    zones = ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"]

    runs = []
    for i in range(n):
        total = random.randint(8, 20)
        completed = random.randint(0, total)

        runs.append({
            "run_id": f"RUN-{datetime.now().strftime('%y%m%d')}-{i + 1:03d}",
            "zone": random.choice(zones),
            "driver_id": f"DRV-{random.randint(100, 109)}",
            "driver_name": random.choice(["Marcus Chen", "Sarah Thompson", "Ahmed Hassan", "Lisa Nguyen", "James Wilson"]),
            "total_stops": total,
            "completed": completed,
            "progress": round(completed / total * 100),
            "estimated_completion": (datetime.now() + timedelta(hours=random.randint(1, 4))).strftime("%H:%M"),
            "status": "active" if completed < total else "completed",
        })

    return pd.DataFrame(runs)
