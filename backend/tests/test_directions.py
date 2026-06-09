"""Locks in the rhumb-line ("compass") bearing model and accurate distances.

Target for all cases: Petronas Towers, Kuala Lumpur (3.1578, 101.7117).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import calculate_direction_distance

KL = (3.1578, 101.7117)

CASES = {
    # name: (lat, lng, expected_8pt_direction_substring, approx_distance_km, tolerance_km)
    "Paris (Eiffel)":   (48.8584, 2.2945, "SE", 10428, 150),
    "Dubai (Burj K)":   (25.1972, 55.2744, "SE", 5532, 150),
    "New York (Statue)": (40.6892, -74.0445, "SE", 15120, 200),
    "Toronto (CN Tower)": (43.6426, -79.3871, "SW", 14810, 200),
}


def _to_8pt(d):
    # collapse 16-point code to its dominant 8-point family for a stable assertion
    mapping = {
        "N": "N", "NNE": "NE", "NE": "NE", "ENE": "NE", "E": "E",
        "ESE": "SE", "SE": "SE", "SSE": "SE", "S": "S",
        "SSW": "SW", "SW": "SW", "WSW": "SW", "W": "W",
        "WNW": "NW", "NW": "NW", "NNW": "NW",
    }
    return mapping[d]


def test_rhumb_bearings_and_distances():
    for name, (lat, lng, exp_dir, exp_dist, tol) in CASES.items():
        direction, distance = calculate_direction_distance(lat, lng, KL[0], KL[1])
        assert _to_8pt(direction) == exp_dir, f"{name}: got {direction} ({_to_8pt(direction)}), expected {exp_dir}"
        assert abs(distance - exp_dist) <= tol, f"{name}: distance {distance} not within {tol} of {exp_dist}"


def test_paris_is_southeast_not_east():
    """Regression for the reported bug: Paris->KL must read SE, not due East."""
    direction, _ = calculate_direction_distance(48.8584, 2.2945, KL[0], KL[1])
    assert _to_8pt(direction) == "SE"


def test_same_latitude_due_east_west():
    # Due east along the equator
    d_east, _ = calculate_direction_distance(0.0, 0.0, 0.0, 50.0)
    assert _to_8pt(d_east) == "E"
    d_west, _ = calculate_direction_distance(0.0, 50.0, 0.0, 0.0)
    assert _to_8pt(d_west) == "W"
