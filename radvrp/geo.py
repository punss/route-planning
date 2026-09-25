"""Synthetic Boston-metro geography.

Travel time = great-circle distance * circuity / speed (DESIGN_NOTES §4).
This is an ASSUMPTION (A3): symmetric, time-invariant, no road network.
Phase 5 replaces it with real road travel times.
"""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0
KM_PER_DEG_LAT = 111.32

# Crude Massachusetts coastline: (lat, max land longitude). A point is "land"
# if its longitude is west of the interpolated coast. Ignores Hull, the harbour
# islands and Cape Ann's fine detail -- good enough to keep hospitals out of
# the bay (R14).
_COAST = np.array([
    (41.95, -70.64), (42.10, -70.70), (42.20, -70.80), (42.27, -70.95),
    (42.31, -71.00), (42.36, -71.03), (42.42, -70.99), (42.47, -70.92),
    (42.52, -70.87), (42.57, -70.77), (42.62, -70.66), (42.66, -70.61),
    (42.70, -70.78), (42.80, -70.81),
])


def on_land(lat: float, lon: float) -> bool:
    return lon < np.interp(lat, _COAST[:, 0], _COAST[:, 1])


def coastline() -> np.ndarray:
    return _COAST.copy()


def offset(center, dist_km: float, bearing_rad: float) -> tuple[float, float]:
    """Point `dist_km` from `center` along `bearing_rad` (flat-earth, fine at metro scale)."""
    lat0, lon0 = center
    dlat = dist_km * np.cos(bearing_rad) / KM_PER_DEG_LAT
    dlon = dist_km * np.sin(bearing_rad) / (KM_PER_DEG_LAT * np.cos(np.radians(lat0)))
    return lat0 + dlat, lon0 + dlon


def to_xy_km(lat, lon, center):
    """Local planar coordinates (km east, km north) relative to `center`, for plotting."""
    lat0, lon0 = center
    x = (np.asarray(lon) - lon0) * KM_PER_DEG_LAT * np.cos(np.radians(lat0))
    y = (np.asarray(lat) - lat0) * KM_PER_DEG_LAT
    return x, y


def haversine_matrix(lat, lon) -> np.ndarray:
    lat = np.radians(np.asarray(lat, dtype=float))
    lon = np.radians(np.asarray(lon, dtype=float))
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def road_matrices(lat, lon, circuity: float, speed_kmh: float):
    """(road distance km, travel time min) matrices."""
    dist = haversine_matrix(lat, lon) * circuity
    return dist, dist / speed_kmh * 60.0
