"""
Real-world Delivery Environment for Reinforcement Learning.

Unlike the original DeliveryEnv (which uses a fake random 10x10 grid),
this environment is built from a real OSRM distance matrix — the same
one the Flask app uses.  The RL agent now trains on actual Klang Valley
road distances, making its decisions meaningful and directly comparable
to the Genetic Algorithm baseline.

Key differences from delivery_env.py
--------------------------------------
- No NetworkX grid.  Distances come from a pre-fetched OSRM matrix.
- State space includes normalised pairwise distances, giving the agent
  a proper spatial sense of the stops.
- Reward is scaled to the actual matrix values so it is consistent
  across different sets of stops.
- Built-in fallback: if OSRM is unavailable it degrades gracefully to
  a Euclidean-distance approximation from raw coordinates.
- Serialisable via `env.to_dict()` / `RealDeliveryEnv.from_dict()` so
  a trained model can be saved and reloaded alongside the stop data it
  was built on.
"""

import math
import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces


# ---------------------------------------------------------------------------
# Helper: Euclidean fallback distance (degrees -> rough km)
# ---------------------------------------------------------------------------

def _haversine_km(lat1, lon1, lat2, lon2):
    """Approximate great-circle distance in km."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _euclidean_matrix(coordinates):
    """Build a distance matrix (metres) from lat/lon pairs as a fallback."""
    n = len(coordinates)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = coordinates[i]
                lat2, lon2 = coordinates[j]
                matrix[i][j] = _haversine_km(lat1, lon1, lat2, lon2) * 1000
    return matrix


# ---------------------------------------------------------------------------
# Main environment
# ---------------------------------------------------------------------------

class RealDeliveryEnv(gym.Env):
    """
    Gymnasium environment for last-mile delivery using real road distances.

    Parameters
    ----------
    distance_matrix : list[list[float]]
        NxN matrix of road distances in **metres** between all stops
        (including the depot at index 0).  Fetched from OSRM.
    coordinates : list[tuple[float, float]]
        Matching list of (lat, lon) pairs, one per row/column of the
        distance matrix.  Used to compute spatial features.
    addresses : list[str], optional
        Human-readable labels for each stop.  Used only for rendering.
    vehicle_type : str
        One of "motorcycle", "car", "van".
    hour_of_day : int or None
        If provided (0-23), bakes a fixed time-of-day into the episode.
        If None, a random hour is sampled each reset so the agent learns
        across all traffic conditions.
    """

    metadata = {"render_modes": ["human"]}

    # kg CO₂ per km — mirrors config.py VEHICLE_EMISSION_RATES
    EMISSION_RATES = {
        "motorcycle": 0.06,
        "car":        0.21,
        "van":        0.35,
    }

    # Time-of-day traffic multipliers (simulated — swappable with live API)
    # Each tuple is (start_hour_inclusive, end_hour_exclusive, multiplier)
    TRAFFIC_SCHEDULE = [
        (7,  10, 2.2),   # morning peak
        (10, 17, 1.1),   # midday light
        (17, 20, 2.5),   # evening peak
        (20, 24, 1.0),   # night free
        (0,   7, 1.0),   # early morning free
    ]

    # Reward weights  (sum = 1.0)
    W_DISTANCE = 0.50
    W_TIME     = 0.30
    W_EMISSION = 0.20

    def __init__(
        self,
        distance_matrix,
        coordinates,
        addresses=None,
        vehicle_type="car",
        hour_of_day=None,
    ):
        super().__init__()

        self.matrix      = distance_matrix
        self.coords      = coordinates
        self.addresses   = addresses or [f"Stop {i}" for i in range(len(coordinates))]
        self.vehicle     = vehicle_type
        self.hour_of_day = hour_of_day

        # Number of stops NOT counting the depot (index 0)
        self.num_stops = len(distance_matrix) - 1
        assert self.num_stops >= 1, "Need at least 2 locations (depot + 1 stop)"

        n = len(distance_matrix)

        # Pre-compute normalisation constant (max finite distance in matrix)
        flat = [
            self.matrix[i][j]
            for i in range(n) for j in range(n)
            if i != j and self.matrix[i][j] is not None
        ]
        self._max_dist = max(flat) if flat else 1.0

        # ── Observation space ────────────────────────────────────────────────
        # [current_stop_idx (normalised),
        #  visited_flags × num_stops,
        #  distances_from_current_to_each_stop (normalised) × num_stops,
        #  traffic_multiplier (normalised)]
        obs_dim = 1 + self.num_stops + self.num_stops + 1
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(obs_dim,), dtype=np.float32
        )

        # ── Action space ─────────────────────────────────────────────────────
        # Agent picks one of the num_stops delivery stops (depot not choosable)
        self.action_space = spaces.Discrete(self.num_stops)

        # Internal state (populated by reset)
        self._current_idx  = 0      # index into distance_matrix (0 = depot)
        self._visited      = []
        self._traffic_mult = 1.0
        self._hour         = 0
        self._total_dist   = 0.0
        self._total_time   = 0.0
        self._total_emiss  = 0.0
        self._step_count   = 0

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self._current_idx = 0   # always start at depot
        self._visited     = [False] * self.num_stops
        self._total_dist  = 0.0
        self._total_time  = 0.0
        self._total_emiss = 0.0
        self._step_count  = 0

        # Determine hour (and traffic multiplier)
        self._hour = (
            self.hour_of_day
            if self.hour_of_day is not None
            else random.randint(0, 23)
        )
        self._traffic_mult = self._get_traffic_multiplier(self._hour)

        return self._get_obs(), {}

    def step(self, action):
        """
        Action is the index of the delivery stop to visit next (0-based,
        depot excluded).  Internally stop i in the action space maps to
        row/column i+1 in the distance matrix.
        """
        # Penalise revisits
        if self._visited[action]:
            return self._get_obs(), -100.0, False, False, {"reason": "revisit_penalty"}

        matrix_idx = action + 1   # shift: action 0 -> matrix row 1, etc.

        # Distance for this leg (metres)
        raw_dist = self.matrix[self._current_idx][matrix_idx]
        if raw_dist is None:
            raw_dist = self._max_dist * 10   # heavy penalty for unreachable

        dist_km   = raw_dist / 1000.0
        time_min  = (dist_km / 35.0) * 60.0 * self._traffic_mult  # 35 km/h urban
        emission  = dist_km * self.EMISSION_RATES.get(self.vehicle, 0.21)

        self._total_dist  += dist_km
        self._total_time  += time_min
        self._total_emiss += emission

        # Multi-objective reward (negative cost, normalised)
        max_dist_km = self._max_dist / 1000.0
        reward = -(
            self.W_DISTANCE * (dist_km  / max(max_dist_km, 1e-6))
            + self.W_TIME   * (time_min / 60.0)          # normalise to hours
            + self.W_EMISSION * emission                  # kg CO₂ already small
            + self._step_count * 0.05                     # small step penalty
        )

        self._visited[action]  = True
        self._current_idx      = matrix_idx
        self._step_count      += 1

        terminated = all(self._visited)

        if terminated:
            # Add return-to-depot leg
            depot_dist = self.matrix[self._current_idx][0]
            if depot_dist is None:
                depot_dist = self._max_dist * 10
            self._total_dist  += depot_dist / 1000.0
            self._total_emiss += (depot_dist / 1000.0) * self.EMISSION_RATES.get(self.vehicle, 0.21)
            self._total_time  += ((depot_dist / 1000.0) / 35.0) * 60.0 * self._traffic_mult
            reward += 100.0   # completion bonus

        info = {
            "total_dist_km": round(self._total_dist,  3),
            "total_time_min": round(self._total_time, 2),
            "total_co2_kg":  round(self._total_emiss, 4),
            "hour_of_day":   self._hour,
            "traffic_mult":  self._traffic_mult,
        }

        return self._get_obs(), reward, terminated, False, info

    def render(self):
        stop_name = (
            self.addresses[self._current_idx]
            if self._current_idx < len(self.addresses)
            else f"idx={self._current_idx}"
        )
        visited_count = sum(self._visited)
        print(
            f"Step {self._step_count:2d} | At: {stop_name[:30]:<30} | "
            f"Visited: {visited_count}/{self.num_stops} | "
            f"Dist: {self._total_dist:.2f} km | "
            f"Time: {self._total_time:.1f} min | "
            f"CO₂: {self._total_emiss:.3f} kg | "
            f"Hour: {self._hour:02d}:00 (×{self._traffic_mult})"
        )

    # ------------------------------------------------------------------
    # Serialisation helpers  (save/load alongside model checkpoints)
    # ------------------------------------------------------------------

    def to_dict(self):
        """Return a plain dict so the env config can be stored as JSON."""
        return {
            "distance_matrix": self.matrix,
            "coordinates":     self.coords,
            "addresses":       self.addresses,
            "vehicle_type":    self.vehicle,
            "hour_of_day":     self.hour_of_day,
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruct env from a saved dict."""
        return cls(
            distance_matrix=data["distance_matrix"],
            coordinates=data["coordinates"],
            addresses=data.get("addresses"),
            vehicle_type=data.get("vehicle_type", "car"),
            hour_of_day=data.get("hour_of_day"),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_obs(self):
        # 1. Current position (normalised by total number of nodes)
        n = len(self.matrix)
        current_norm = self._current_idx / max(n - 1, 1)

        # 2. Visited flags
        visited_flags = [float(v) for v in self._visited]

        # 3. Distances from current position to each delivery stop (normalised)
        dist_features = []
        for stop_action in range(self.num_stops):
            matrix_idx = stop_action + 1
            d = self.matrix[self._current_idx][matrix_idx]
            if d is None:
                d = self._max_dist
            dist_features.append(d / self._max_dist)

        # 4. Traffic multiplier (normalised: max expected mult is 2.5)
        traffic_norm = self._traffic_mult / 2.5

        obs = np.array(
            [current_norm] + visited_flags + dist_features + [traffic_norm],
            dtype=np.float32,
        )
        return obs

    @staticmethod
    def _get_traffic_multiplier(hour):
        schedule = [
            (7,  10, 2.2),
            (10, 17, 1.1),
            (17, 20, 2.5),
            (20, 24, 1.0),
            (0,   7, 1.0),
        ]
        for start, end, mult in schedule:
            if start <= hour < end:
                return mult
        return 1.0


# ---------------------------------------------------------------------------
# Factory: build env directly from OSRM (used by Flask and training script)
# ---------------------------------------------------------------------------

def make_env_from_osrm(addresses, vehicle_type="car", hour_of_day=None):
    """
    Geocode addresses and fetch a real OSRM distance matrix, then return
    a ready-to-use RealDeliveryEnv.

    Parameters
    ----------
    addresses : list[str]
        Human-readable addresses.  First entry is treated as the depot.
    vehicle_type : str
        "motorcycle", "car", or "van".
    hour_of_day : int or None
        If set, fixes the traffic multiplier for every episode.

    Returns
    -------
    env : RealDeliveryEnv  (or None if geocoding / OSRM fails)
    coordinates : list[tuple]  (lat, lon) pairs in the same order
    valid_addresses : list[str]
    """
    # Import here to avoid circular imports when used inside Flask
    from app.services.geo_service import get_coordinates, get_distance_matrix

    print(f"\n[RealDeliveryEnv] Geocoding {len(addresses)} addresses…")
    coordinates    = []
    valid_addresses = []

    for addr in addresses:
        coord = get_coordinates(addr)
        if coord:
            coordinates.append(coord)
            valid_addresses.append(addr)
        else:
            print(f"  ✗ Could not geocode: {addr}")

    if len(coordinates) < 2:
        print("[RealDeliveryEnv] ✗ Need at least 2 valid addresses.")
        return None, [], []

    print(f"[RealDeliveryEnv] Fetching OSRM distance matrix…")
    matrix = get_distance_matrix(coordinates)

    if matrix is None:
        print("[RealDeliveryEnv] ✗ OSRM failed — falling back to Euclidean distances.")
        matrix = _euclidean_matrix(coordinates)

    env = RealDeliveryEnv(
        distance_matrix=matrix,
        coordinates=coordinates,
        addresses=valid_addresses,
        vehicle_type=vehicle_type,
        hour_of_day=hour_of_day,
    )
    print(f"[RealDeliveryEnv] ✓ Env ready: {len(valid_addresses)} stops, vehicle={vehicle_type}")
    return env, coordinates, valid_addresses