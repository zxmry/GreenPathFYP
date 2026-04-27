# 🌿 GreenPath — Smart Delivery Optimizer

A Flask-based web application for optimizing last-mile delivery routes using a **Genetic Algorithm** (TSP solver). Includes a reinforcement learning (DQN) training pipeline for research purposes.

---

## 📁 Project Structure

```
GreenPath/
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── config.py                  # Centralized configuration
├── run.py                     # Flask entry point
│
├── app/                       # Flask web application
│   ├── __init__.py            # App factory
│   ├── auth.py                # Login / signup / logout
│   ├── api.py                 # /api/process-route endpoint
│   ├── core/                  # Business logic
│   │   ├── metrics.py         # Time, CO₂, fuel cost calculations
│   │   └── routing.py         # Original route distance calc
│   ├── services/              # External API wrappers
│   │   └── geo_service.py     # Geocoding (Nominatim) + OSRM
│   └── solver/                # Optimization algorithms
│       └── genetic.py         # Genetic Algorithm TSP solver
│
├── rl/                        # Reinforcement Learning package
│   ├── delivery_env.py        # Custom Gymnasium environment
│   └── train_dqn.py           # DQN training & evaluation
│
├── static/                    # CSS, JS, images
├── templates/                 # HTML templates
├── models/                    # Saved RL models
└── logs/                      # Training logs
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The RL training scripts require additional packages (`stable-baselines3`, `gymnasium`, `matplotlib`). Install them separately if needed:
> ```bash
> pip install stable-baselines3 gymnasium matplotlib
> ```

### 2. Run the Flask App

```bash
python run.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🧬 How It Works

1. **Geocoding** — Converts user-entered addresses to coordinates via Nominatim.
2. **Distance Matrix** — Fetches real road distances between all stops via OSRM.
3. **Original Route** — Calculates the distance of the user's input order.
4. **Genetic Algorithm** — Optimizes the stop sequence to minimize total distance.
5. **Metrics** — Computes time saved, CO₂ reduction, and fuel cost savings.
6. **Visualization** — Displays original vs. optimized routes on an interactive map.

---

## 🤖 Reinforcement Learning (Optional)

Train a DQN agent on a simulated delivery environment:

```bash
python -m rl.train_dqn
```

Results are saved to `models/` and `logs/`. A training curve is exported to `training_curve.png`.

---

## ⚙️ Configuration

Edit `config.py` to adjust:

- `SECRET_KEY` — Flask session secret (change in production!)
- `VEHICLE_FUEL_PARAMS` — Fuel efficiency & Malaysian fuel prices
- `ROUTE_PARAMS` — Average speed, stop time, traffic factor, CO₂ rate
- `GA_DEFAULTS` — Genetic algorithm population size & generations

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Maps | Leaflet.js + OpenStreetMap |
| Charts | Chart.js |
| Geocoding | Nominatim (OpenStreetMap) |
| Routing | OSRM (Open Source Routing Machine) |
| Optimization | Custom Genetic Algorithm |
| RL Training | Stable-Baselines3 (DQN) |

---

## 📄 License

Student FYP project — for academic use only.

