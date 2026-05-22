"""
Training script for DQN on the real OSRM-based delivery environment.

Usage
-----
# Train on a hardcoded set of Klang Valley stops (good for FYP demo):
    python -m rl.train_real_dqn

# Train on your own addresses (passed as CLI args):
    python -m rl.train_real_dqn \
        --addresses "KLCC, Kuala Lumpur" "Petaling Jaya City Centre" \
                    "Subang Jaya, Selangor" "Shah Alam, Selangor" \
        --vehicle car \
        --timesteps 150000

# Evaluate a saved model without retraining:
    python -m rl.train_real_dqn --eval-only

What this script does differently from train_dqn.py
----------------------------------------------------
1.  Builds the environment from real OSRM data (no fake grid).
2.  Trains across all hours of the day (random hour each episode) so
    the agent learns time-of-day traffic awareness.
3.  Saves the env config alongside the model so they can be reloaded
    together in Flask without re-geocoding.
4.  Produces a proper comparison: random-agent baseline vs DQN vs GA.
"""

import argparse
import json
import os
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless — no display needed on the server
import matplotlib.pyplot as plt

from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback

from rl.real_delivery_env import RealDeliveryEnv, make_env_from_osrm

# ---------------------------------------------------------------------------
# Default demo addresses (Klang Valley landmarks — no API key needed)
# ---------------------------------------------------------------------------

DEFAULT_ADDRESSES = [
    "KLCC, Kuala Lumpur",                    # depot (index 0)
    "Petaling Jaya City Centre, Selangor",
    "Subang Jaya, Selangor",
    "Shah Alam, Selangor",
    "Chow Kit, Kuala Lumpur",
    "Bangsar, Kuala Lumpur",
]

MODELS_DIR = "models"
LOGS_DIR   = "logs"


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class EpisodeRewardCallback(BaseCallback):
    """Collect per-episode rewards for the learning-curve plot."""

    def __init__(self):
        super().__init__()
        self.episode_rewards = []
        self._running = {}

    def _on_step(self):
        for i, done in enumerate(self.locals["dones"]):
            r = self.locals["rewards"][i]
            self._running[i] = self._running.get(i, 0.0) + r
            if done:
                self.episode_rewards.append(self._running[i])
                self._running[i] = 0.0
        return True


# ---------------------------------------------------------------------------
# Baseline: random agent
# ---------------------------------------------------------------------------

def run_random_baseline(env, n_episodes=50):
    """Evaluate a random agent to establish a baseline."""
    results = []
    for _ in range(n_episodes):
        obs, _ = env.reset()
        done = False
        while not done:
            action = env.action_space.sample()
            obs, _, terminated, truncated, info = env.step(action)
            done = terminated or truncated
        results.append(info)

    avg_dist  = np.mean([r["total_dist_km"]  for r in results])
    avg_time  = np.mean([r["total_time_min"] for r in results])
    avg_co2   = np.mean([r["total_co2_kg"]   for r in results])
    print(f"\n[Baseline — Random Agent] over {n_episodes} episodes:")
    print(f"  Avg distance : {avg_dist:.2f} km")
    print(f"  Avg time     : {avg_time:.1f} min")
    print(f"  Avg CO₂      : {avg_co2:.4f} kg")
    return {"avg_dist_km": avg_dist, "avg_time_min": avg_time, "avg_co2_kg": avg_co2}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(env, total_timesteps=150_000, model_tag="real"):
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR,   exist_ok=True)

    train_env = Monitor(env)
    eval_env  = Monitor(RealDeliveryEnv.from_dict(env.to_dict()))

    reward_cb = EpisodeRewardCallback()
    eval_cb   = EvalCallback(
        eval_env,
        best_model_save_path=f"{MODELS_DIR}/",
        log_path=f"{LOGS_DIR}/",
        eval_freq=max(total_timesteps // 30, 1000),
        n_eval_episodes=15,
        verbose=0,
    )

    model = DQN(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=5e-4,
        buffer_size=50_000,
        learning_starts=500,
        batch_size=64,
        tau=0.005,
        gamma=0.99,
        train_freq=4,
        target_update_interval=500,
        exploration_fraction=0.25,
        exploration_final_eps=0.05,
        verbose=0,
        policy_kwargs=dict(net_arch=[256, 256, 128]),
    )

    print(f"\n[Training] DQN for {total_timesteps:,} timesteps…")
    t0 = time.time()
    model.learn(total_timesteps=total_timesteps, callback=[reward_cb, eval_cb])
    elapsed = time.time() - t0
    print(f"[Training] Done in {elapsed:.1f}s")

    final_path = f"{MODELS_DIR}/dqn_{model_tag}_final"
    model.save(final_path)
    print(f"[Training] Model saved → {final_path}.zip")

    return model, reward_cb.episode_rewards


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model, env, n_episodes=30):
    results = []
    for ep in range(n_episodes):
        obs, _ = env.reset()
        done   = False
        route  = [0]   # depot first

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, _, terminated, truncated, info = env.step(int(action))
            done = terminated or truncated
            route.append(int(action) + 1)

        route.append(0)   # return to depot
        results.append({**info, "route": route})

    avg_dist = np.mean([r["total_dist_km"]  for r in results])
    avg_time = np.mean([r["total_time_min"] for r in results])
    avg_co2  = np.mean([r["total_co2_kg"]   for r in results])

    print(f"\n[Evaluation — DQN Agent] over {n_episodes} episodes:")
    print(f"  Avg distance : {avg_dist:.2f} km")
    print(f"  Avg time     : {avg_time:.1f} min")
    print(f"  Avg CO₂      : {avg_co2:.4f} kg")
    print(f"  Sample route : {results[0]['route']}")
    return {
        "avg_dist_km":  avg_dist,
        "avg_time_min": avg_time,
        "avg_co2_kg":   avg_co2,
        "episodes":     results,
    }


# ---------------------------------------------------------------------------
# GA baseline comparison (calls the existing GeneticOptimizer)
# ---------------------------------------------------------------------------

def ga_baseline(matrix):
    """Run the existing GA on the same matrix for a fair comparison."""
    try:
        from app.solver.genetic import GeneticOptimizer
        from config import GA_DEFAULTS

        optimizer = GeneticOptimizer(
            distance_matrix=matrix,
            pop_size=GA_DEFAULTS["pop_size"],
            generations=GA_DEFAULTS["generations"],
        )
        route, dist_m = optimizer.solve()
        dist_km = dist_m / 1000.0
        print(f"\n[Baseline — Genetic Algorithm]:")
        print(f"  Distance     : {dist_km:.2f} km")
        print(f"  Route        : {route} → {route[0]}")
        return {"dist_km": dist_km, "route": route}
    except Exception as e:
        print(f"[GA Baseline] Could not run: {e}")
        return None


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_results(episode_rewards, dqn_result, random_result, ga_result, tag="real"):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── Left: learning curve ──────────────────────────────────────────────
    ax = axes[0]
    rewards = np.array(episode_rewards)
    ax.plot(rewards, alpha=0.25, color="#4B9CD3", linewidth=0.8, label="Episode reward")
    window = min(50, max(1, len(rewards) // 20))
    if len(rewards) >= window:
        smoothed = np.convolve(rewards, np.ones(window) / window, mode="valid")
        ax.plot(smoothed, color="#4B9CD3", linewidth=2, label=f"Smoothed (w={window})")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Total reward")
    ax.set_title("DQN Learning Curve (Real OSRM Env)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # ── Right: comparison bar chart ───────────────────────────────────────
    ax2 = axes[1]
    labels, values, colors = [], [], []

    labels.append("Random agent");  values.append(random_result["avg_dist_km"]);  colors.append("#E57373")
    labels.append("DQN (ours)");    values.append(dqn_result["avg_dist_km"]);     colors.append("#4B9CD3")
    if ga_result:
        labels.append("Genetic Alg"); values.append(ga_result["dist_km"]); colors.append("#81C784")

    bars = ax2.bar(labels, values, color=colors, edgecolor="white", linewidth=1.2)
    ax2.set_ylabel("Average distance (km)")
    ax2.set_title("Algorithm Comparison — Total Route Distance")
    ax2.grid(True, axis="y", alpha=0.3)

    for bar, val in zip(bars, values):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{val:.2f} km",
            ha="center", va="bottom", fontsize=9,
        )

    plt.tight_layout()
    out_path = f"training_curve_{tag}.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"\n[Plot] Saved → {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train DQN on real OSRM delivery env")
    parser.add_argument(
        "--addresses", nargs="+", default=DEFAULT_ADDRESSES,
        help="Addresses to use (first = depot)",
    )
    parser.add_argument("--vehicle",    default="car",     choices=["car", "motorcycle", "van"])
    parser.add_argument("--timesteps",  type=int, default=150_000)
    parser.add_argument("--eval-only",  action="store_true",
                        help="Skip training; load saved model for evaluation")
    parser.add_argument("--model-tag",  default="real",
                        help="Suffix for saved model filenames")
    args = parser.parse_args()

    # 1. Build env from OSRM
    env, coordinates, valid_addresses = make_env_from_osrm(
        args.addresses, vehicle_type=args.vehicle
    )

    if env is None:
        print("Could not build environment. Check your address list and OSRM connectivity.")
        return

    # 2. Save env config so Flask can reload it without re-geocoding
    env_config_path = f"{MODELS_DIR}/env_config_{args.model_tag}.json"
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(env_config_path, "w") as f:
        json.dump(env.to_dict(), f, indent=2)
    print(f"[Config] Env config saved → {env_config_path}")

    # 3. Random baseline
    random_result = run_random_baseline(env, n_episodes=50)

    # 4. GA baseline
    ga_result = ga_baseline(env.matrix)

    if args.eval_only:
        # Load existing model
        model_path = f"{MODELS_DIR}/dqn_{args.model_tag}_final"
        print(f"\n[Eval Only] Loading model from {model_path}.zip")
        model = DQN.load(model_path, env=Monitor(env))
        episode_rewards = []
    else:
        # Train
        model, episode_rewards = train(env, total_timesteps=args.timesteps, model_tag=args.model_tag)

    # 5. Evaluate
    eval_env    = RealDeliveryEnv.from_dict(env.to_dict())
    dqn_result  = evaluate(model, eval_env, n_episodes=30)

    # 6. Save results summary
    summary = {
        "addresses":      valid_addresses,
        "vehicle":        args.vehicle,
        "random_baseline": random_result,
        "ga_baseline":    ga_result,
        "dqn_result": {
            "avg_dist_km":  dqn_result["avg_dist_km"],
            "avg_time_min": dqn_result["avg_time_min"],
            "avg_co2_kg":   dqn_result["avg_co2_kg"],
        },
    }
    summary_path = f"{MODELS_DIR}/results_{args.model_tag}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[Results] Summary saved → {summary_path}")

    # 7. Print final comparison
    print("\n" + "=" * 55)
    print("FINAL COMPARISON")
    print("=" * 55)
    print(f"  Random agent : {random_result['avg_dist_km']:.2f} km")
    if ga_result:
        diff_ga = random_result['avg_dist_km'] - ga_result['dist_km']
        print(f"  GA           : {ga_result['dist_km']:.2f} km  (-{diff_ga:.2f} km vs random)")
    diff_dqn = random_result['avg_dist_km'] - dqn_result['avg_dist_km']
    print(f"  DQN (ours)   : {dqn_result['avg_dist_km']:.2f} km  (-{diff_dqn:.2f} km vs random)")
    print("=" * 55)

    # 8. Plot
    if episode_rewards:
        plot_results(episode_rewards, dqn_result, random_result, ga_result, tag=args.model_tag)


if __name__ == "__main__":
    main()