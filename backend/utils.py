import math
import hashlib
from datetime import datetime, timezone
from data.buildings import BUILDINGS


def to_radians(degrees):
    return degrees * math.pi / 180


def to_degrees(radians):
    return radians * 180 / math.pi


def calculate_direction_distance(guess_lat, guess_lng, correct_lat, correct_lng):
    phi1 = to_radians(guess_lat)
    phi2 = to_radians(correct_lat)
    # Rhumb-line (loxodrome) bearing: the constant compass heading you would follow
    # on a flat (Mercator) map. Matches player intuition better than the great-circle
    # initial bearing, which points "over the pole" for long/near-antipodal distances.
    delta_lambda = to_radians(correct_lng - guess_lng)
    # Take the shorter east/west way around the globe.
    if abs(delta_lambda) > math.pi:
        delta_lambda -= math.copysign(2 * math.pi, delta_lambda)
    delta_psi = math.log(
        math.tan(math.pi / 4 + phi2 / 2) / math.tan(math.pi / 4 + phi1 / 2)
    )
    theta = math.atan2(delta_lambda, delta_psi)
    bearing = (to_degrees(theta) + 360) % 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(bearing / 22.5) % 16
    direction = points[index]
    R = 6371
    delta_phi = to_radians(correct_lat - guess_lat)
    delta_lambda2 = to_radians(correct_lng - guess_lng)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda2 / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = round(R * c)
    return direction, distance


def get_daily_building_id(date_str: str) -> str:
    seed = hashlib.md5(f"silhouettele-{date_str}".encode(), usedforsecurity=False).hexdigest()
    index = int(seed, 16) % len(BUILDINGS)
    return BUILDINGS[index]["building_id"]


def get_today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


_BUILDINGS_BY_ID = {b["building_id"]: b for b in BUILDINGS}


def get_building_by_id(building_id: str):
    return _BUILDINGS_BY_ID.get(building_id)


def get_direction_arrow(direction: str) -> str:
    arrows = {
        "N": "\u2191", "NNE": "\u2197", "NE": "\u2197", "ENE": "\u2197",
        "E": "\u2192", "ESE": "\u2198", "SE": "\u2198", "SSE": "\u2198",
        "S": "\u2193", "SSW": "\u2199", "SW": "\u2199", "WSW": "\u2199",
        "W": "\u2190", "WNW": "\u2196", "NW": "\u2196", "NNW": "\u2196"
    }
    return arrows.get(direction, "")
