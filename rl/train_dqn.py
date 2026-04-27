import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
from stable_baselines3.common.monitor import Monitor

from rl.delivery_env import DeliveryEnv


# ── Reward logger callback ─────────────────────────────────────────────────────
class RewardLoggerCallback(BaseCallback):
    """Track episode rewards during training for plotting."""

    def __init__(self):
        super().__init__()
        self.episode_rewards = []
        self._current_rewards = {}

    def _on_step(self):
        for i, done in enumerate(self.locals["dones"]):
            reward = self.locals["rewards"][i]
            self._current_rewards[i] = self._current_rewards.get(i, 0) + reward
            if done:
                self.episode_rewards.append(self._current_rewards[i])
                self._current_rewards[i] = 0
        return True


def make_env(num_stops=5, vehicle_type="car"):
    def _init():
        env = DeliveryEnv(num_stops=num_stops, vehicle_type=vehicle_type)
        return Monitor(env)
    return _init


def train(num_stops=5, vehicle_type="car", total_timesteps=100_000):

    print(f"Training DQN | Stops: {num_stops} | Vehicle: {vehicle_type}")

    # Vectorised environment (4 parallel envs speeds up training)
    train_env = make_vec_env(
        make_env(num_stops, vehicle_type),
        n_envs=4
    )

    # Separate eval environment
    eval_env = Monitor(DeliveryEnv(num_stops=num_stops, vehicle_type=vehicle_type))

    reward_logger = RewardLoggerCallback()

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="./models/",
        log_path="./logs/",
        eval_freq=5000,
        n_eval_episodes=10,
        verbose=1,
    )

    # DQN model
    model = DQN(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=1e-3,
        buffer_size=50_000,
        learning_starts=1000,
        batch_size=64,
        tau=0.005,                  # Soft update coefficient
        gamma=0.99,                 # Discount factor
        train_freq=4,
        target_update_interval=500,
        exploration_fraction=0.2,   # Explore for first 20% of training
        exploration_final_eps=0.05,
        verbose=1,
        policy_kwargs=dict(net_arch=[256, 256]),  # 2-layer MLP
    )

    model.learn(
        total_timesteps=total_timesteps,
        callback=[reward_logger, eval_callback],
    )

    model.save("models/dqn_delivery_final")
    print("Model saved to models/dqn_delivery_final")

    return model, reward_logger.episode_rewards


def evaluate(model, num_stops=5, vehicle_type="car", n_episodes=20):
    """Run trained agent and collect delivery metrics."""

    env = DeliveryEnv(num_stops=num_stops, vehicle_type=vehicle_type)
    results = []

    for ep in range(n_episodes):
        obs, _ = env.reset()
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

        results.append({
            "episode":  ep + 1,
            "time_min": info.get("time_min", 0),
            "dist_km":  info.get("dist_km", 0),
            "emission": info.get("emission", 0),
        })

    avg_time  = np.mean([r["time_min"] for r in results])
    avg_dist  = np.mean([r["dist_km"]  for r in results])
    avg_emiss = np.mean([r["emission"] for r in results])

    print(f"\n=== Evaluation over {n_episodes} episodes ===")
    print(f"Avg travel time : {avg_time:.1f} min")
    print(f"Avg distance    : {avg_dist:.2f} km")
    print(f"Avg CO2 emission: {avg_emiss:.3f} kg")

    return results


def plot_training(episode_rewards):
    """Plot learning curve with smoothed moving average."""

    rewards = np.array(episode_rewards)

    # Smooth with window size 50
    window = 50
    if len(rewards) >= window:
        smoothed = np.convolve(rewards, np.ones(window) / window, mode="valid")
    else:
        smoothed = rewards

    plt.figure(figsize=(10, 4))
    plt.plot(rewards,  alpha=0.3, color="steelblue", label="Raw reward")
    plt.plot(smoothed, color="steelblue", linewidth=2, label=f"Smoothed (w={window})")
    plt.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    plt.xlabel("Episode")
    plt.ylabel("Total reward")
    plt.title("DQN Learning Curve — Delivery Optimisation")
    plt.legend()
    plt.tight_layout()
    plt.savefig("training_curve.png", dpi=150)
    plt.show()
    print("Saved training_curve.png")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    model, episode_rewards = train(
        num_stops=5,
        vehicle_type="car",
        total_timesteps=100_000,
    )

    evaluate(model, num_stops=5, vehicle_type="car", n_episodes=20)

    plot_training(episode_rewards)

