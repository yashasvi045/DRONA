import math
from typing import List, Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two GPS points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


class Drone:
    """
    Simulates a drone flying along a sequence of (lat, lon) waypoints.
    Moves at a fixed speed and advances in discrete time steps.
    """

    SPEED_KMH = 50.0  # simulated cruise speed

    def __init__(self, drone_id: str, route_name: str, waypoints: List[Tuple[float, float]]):
        if len(waypoints) < 2:
            raise ValueError("A route needs at least 2 waypoints.")
        self.drone_id   = drone_id
        self.route_name = route_name
        self.waypoints  = waypoints

        self.lat, self.lon = waypoints[0]
        self._seg      = 0      # index of current segment's start waypoint
        self._progress = 0.0    # 0.0 → 1.0 along the current segment
        self.finished  = False
        self.triggered_nodes: set = set()  # node IDs already logged this trip

    # ─── Movement ────────────────────────────────────────────────────────────

    def step(self, tick_seconds: float) -> None:
        """Advance the drone by tick_seconds of simulated flight time."""
        if self.finished:
            return

        a_lat, a_lon = self.waypoints[self._seg]
        b_lat, b_lon = self.waypoints[self._seg + 1]
        seg_km = haversine_km(a_lat, a_lon, b_lat, b_lon)

        if seg_km < 1e-9:
            self._advance_segment()
            return

        step_frac = (self.SPEED_KMH * tick_seconds / 3600.0) / seg_km
        self._progress += step_frac

        if self._progress >= 1.0:
            self._advance_segment()
        else:
            self.lat = a_lat + (b_lat - a_lat) * self._progress
            self.lon = a_lon + (b_lon - a_lon) * self._progress

    def _advance_segment(self) -> None:
        self._seg     += 1
        self._progress = 0.0
        if self._seg >= len(self.waypoints) - 1:
            self.lat, self.lon = self.waypoints[-1]
            self.finished = True
        else:
            self.lat, self.lon = self.waypoints[self._seg]

    # ─── Node proximity ──────────────────────────────────────────────────────

    def check_node_proximity(self, nodes: dict, radius_km: float) -> List[str]:
        """
        Return IDs of nodes within radius_km that haven't been triggered yet.
        Marks them as triggered so they are only logged once per trip.
        """
        newly_triggered = []
        for node_id, node in nodes.items():
            if node_id in self.triggered_nodes:
                continue
            dist = haversine_km(self.lat, self.lon, node["lat"], node["lon"])
            if dist <= radius_km:
                self.triggered_nodes.add(node_id)
                newly_triggered.append(node_id)
        return newly_triggered
