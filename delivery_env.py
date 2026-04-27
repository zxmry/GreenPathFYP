import gymnasium as gym
import numpy as np
import networkx as nx
from gymnasium import spaces
import random

class DeliveryEnv(gym.Env):
    """
    Custom Gymnasium environment for last-mile delivery optimisation.
    
    - Up to 10 delivery stops on a road graph
    - Simulated traffic conditions (light / moderate / heavy)
    - Multi-objective reward: time + distance + carbon emission
    """

    metadata = {"render_modes": ["human"]}

    TRAFFIC_MULTIPLIERS = {
        "light":    1.0,
        "moderate": 1.5,
        "heavy":    2.5,
    }

    VEHICLE_EMISSION_RATES = {
        "motorcycle": 0.06,   # kg CO2 per km
        "car":        0.21,
        "van":        0.35,
    }

    def __init__(self, num_stops=5, vehicle_type="car", grid_size=10):
        super().__init__()

        self.num_stops   = num_stops
        self.vehicle     = vehicle_type
        self.grid_size   = grid_size
        self.num_nodes   = grid_size * grid_size  # 100 road intersections

        # ── Action space ──────────────────────────────────────────
        # Agent picks which unvisited stop to go to next (0 to num_stops-1)
        self.action_space = spaces.Discrete(self.num_stops)

        # ── Observation space ──────────────────────────────────────
        # [current_node, visited_flags x num_stops, traffic_level x num_stops]
        obs_size = 1 + self.num_stops + self.num_stops
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(obs_size,), dtype=np.float32
        )

        # Reward weights (tune these for your FYP balance)
        self.w_time     = 0.4
        self.w_distance = 0.4
        self.w_emission = 0.2

        self._build_road_graph()

    def _build_road_graph(self):
        """Build a grid road network using NetworkX."""
        self.G = nx.grid_2d_graph(self.grid_size, self.grid_size)

        # Assign random base distances to edges (in km)
        for u, v in self.G.edges():
            self.G[u][v]["distance"] = round(random.uniform(0.3, 1.5), 2)

        # Map 2D grid coords to flat node IDs for easier indexing
        self.node_list = list(self.G.nodes())
        self.node_index = {n: i for i, n in enumerate(self.node_list)}

    def _get_traffic(self):
        """Randomly simulate traffic condition for each stop."""
        levels = list(self.TRAFFIC_MULTIPLIERS.keys())
        return [random.choice(levels) for _ in range(self.num_stops)]

    def _get_travel_time(self, from_node, to_node, traffic_level):
        """Estimate travel time in minutes between two nodes."""
        try:
            path = nx.shortest_path(self.G, from_node, to_node, weight="distance")
            dist = sum(
                self.G[path[i]][path[i+1]]["distance"]
                for i in range(len(path) - 1)
            )
        except nx.NetworkXNoPath:
            dist = 999  # Unreachable penalty

        multiplier = self.TRAFFIC_MULTIPLIERS[traffic_level]
        avg_speed_kmh = 40
        time_minutes = (dist / avg_speed_kmh) * 60 * multiplier
        return time_minutes, dist

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # Randomly place depot and delivery stops on the graph
        chosen = random.sample(self.node_list, self.num_stops + 1)
        self.depot    = chosen[0]
        self.stops    = chosen[1:]

        self.current_node = self.depot
        self.visited      = [False] * self.num_stops
        self.traffic      = self._get_traffic()
        self.total_time   = 0.0
        self.total_dist   = 0.0
        self.total_emiss  = 0.0
        self.step_count   = 0

        return self._get_obs(), {}

    def _get_obs(self):
        current_idx = self.node_index[self.current_node] / self.num_nodes
        visited_flags = [float(v) for v in self.visited]
        traffic_enc = [
            list(self.TRAFFIC_MULTIPLIERS.keys()).index(t) / 2.0
            for t in self.traffic
        ]
        obs = np.array([current_idx] + visited_flags + traffic_enc, dtype=np.float32)
        return obs

    def step(self, action):
        # If already visited, penalise
        if self.visited[action]:
            reward = -50
            obs = self._get_obs()
            return obs, reward, False, False, {"reason": "revisit_penalty"}

        target_node   = self.stops[action]
        traffic_level = self.traffic[action]

        time_min, dist_km = self._get_travel_time(
            self.current_node, target_node, traffic_level
        )

        emission = dist_km * self.VEHICLE_EMISSION_RATES[self.vehicle]

        self.total_time  += time_min
        self.total_dist  += dist_km
        self.total_emiss += emission

        # Multi-objective reward (negative = cost to minimise)
        reward = -(
            self.w_time     * time_min / 30     +   # normalised ~30 min
            self.w_distance * dist_km  / 5      +   # normalised ~5 km
            self.w_emission * emission / 1      +   # kg CO2
            self.step_count * 0.1                   # small step penalty
        )

        self.visited[action] = True
        self.current_node    = target_node
        self.step_count     += 1

        terminated = all(self.visited)

        # Bonus for completing all deliveries
        if terminated:
            reward += 50

        return self._get_obs(), reward, terminated, False, {
            "time_min":  self.total_time,
            "dist_km":   self.total_dist,
            "emission":  self.total_emiss,
        }

    def render(self):
        print(f"Step {self.step_count} | Node: {self.current_node} | "
              f"Visited: {sum(self.visited)}/{self.num_stops} | "
              f"Time: {self.total_time:.1f}min | "
              f"Dist: {self.total_dist:.2f}km | "
              f"CO2: {self.total_emiss:.3f}kg")


if __name__ == "__main__":
    from gymnasium.utils.env_checker import check_env

    env = DeliveryEnv(num_stops=5, vehicle_type="car")
    check_env(env)
    
    obs, _ = env.reset()
    print("Initial obs shape:", obs.shape)
    print("Action space:", env.action_space)

    for _ in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        env.render()
        if terminated:
            print("All stops delivered!", info)
            break
