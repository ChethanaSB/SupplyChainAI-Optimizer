"""
rl_agent.py — Reinforcement Learning inventory agent using Stable-Baselines3 PPO.
Custom Gymnasium environment for inventory optimization.
"""
import logging
import math
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("chainmind.rl_agent")

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "rl_ppo_inventory.zip"


class InventoryEnv:
    """
    Custom Gymnasium environment for inventory management.

    State: (stock_level, forecast_mean, forecast_p90, risk_score,
             pending_orders, unit_cost) — normalized 0-1

    Action: order quantity as fraction of EOQ (0 to 3)
    Reward: −holding_cost − stockout_penalty − order_cost
    """

    def __init__(
        self,
        demand_avg: float = 200.0,
        demand_std: float = 50.0,
        lead_time: float = 14.0,
        unit_cost: float = 100.0,
        holding_rate: float = 0.25,
        stockout_penalty: float = 500.0,
        order_cost: float = 150.0,
        eoq: float = 500.0,
        seed: int = 42,
    ):
        self.demand_avg = demand_avg
        self.demand_std = demand_std
        self.lead_time = int(lead_time)
        self.unit_cost = unit_cost
        self.holding_rate = holding_rate
        self.stockout_penalty = stockout_penalty
        self.order_cost = order_cost
        self.eoq = eoq
        self.rng = np.random.default_rng(seed)

        # Gymnasium-compatible spaces
        try:
            import gymnasium as gym
            self.observation_space = gym.spaces.Box(
                low=np.zeros(6, dtype=np.float32),
                high=np.ones(6, dtype=np.float32),
                dtype=np.float32,
            )
            self.action_space = gym.spaces.Box(
                low=np.array([0.0], dtype=np.float32),
                high=np.array([3.0], dtype=np.float32),
                dtype=np.float32,
            )
        except ImportError:
            logger.warning("gymnasium not installed — RL env in limited mode")

        self.reset()

    def reset(self, seed=None):
        """Reset environment state."""
        self.t = 0
        self.stock = self.eoq  # Start with one EOQ in stock
        self.pipeline: list[tuple[int, float]] = []  # (arrival_day, quantity)
        self.risk_score = float(self.rng.uniform(0, 50))
        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        # Normalize all features to [0, 1]
        max_stock = self.eoq * 5
        forecast_mean = self.demand_avg * self.lead_time
        forecast_p90 = forecast_mean * 1.3
        obs = np.array([
            min(1.0, self.stock / max_stock),
            min(1.0, forecast_mean / (max_stock * 2)),
            min(1.0, forecast_p90 / (max_stock * 2)),
            self.risk_score / 100.0,
            min(1.0, sum(q for _, q in self.pipeline) / max_stock),
            min(1.0, self.unit_cost / 5000.0),
        ], dtype=np.float32)
        return obs

    def step(self, action: np.ndarray):
        order_qty = max(0.0, float(action[0]) * self.eoq)

        # Place order (arrives after lead_time days)
        if order_qty > 0:
            self.pipeline.append((self.t + self.lead_time, order_qty))

        # Receive orders
        arrived = [q for (t, q) in self.pipeline if t <= self.t]
        self.stock += sum(arrived)
        self.pipeline = [(t, q) for (t, q) in self.pipeline if t > self.t]

        # Simulate demand
        demand = max(0, int(self.rng.normal(self.demand_avg, self.demand_std)))
        fulfilled = min(self.stock, demand)
        shortfall = max(0, demand - self.stock)
        self.stock = max(0, self.stock - demand)

        # Compute costs
        holding_cost = self.stock * self.unit_cost * self.holding_rate / 365
        stockout_cost = shortfall * self.stockout_penalty
        order_cost_val = self.order_cost if order_qty > 0 else 0

        reward = -(holding_cost + stockout_cost + order_cost_val) / 1000.0

        # Update risk score (random walk)
        self.risk_score = float(np.clip(
            self.risk_score + self.rng.normal(0, 5),
            0, 100
        ))
        self.t += 1

        obs = self._get_obs()
        terminated = self.t >= 365
        truncated = False
        info = {
            "holding_cost": holding_cost,
            "stockout_cost": stockout_cost,
            "order_qty": order_qty,
            "demand": demand,
            "fulfilled": fulfilled,
            "stock": self.stock,
        }
        return obs, reward, terminated, truncated, info


def train_rl_agent(
    demand_avg: float = 200.0,
    demand_std: float = 50.0,
    lead_time: float = 14.0,
    unit_cost: float = 100.0,
    total_timesteps: int = 500_000,
) -> dict:
    """Train PPO agent on inventory environment."""
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_util import make_vec_env
        import gymnasium as gym
    except ImportError:
        raise ImportError(
            "stable-baselines3 and gymnasium not installed. "
            "Run: pip install stable-baselines3 gymnasium"
        )

    env = InventoryEnv(demand_avg=demand_avg, demand_std=demand_std,
                       lead_time=lead_time, unit_cost=unit_cost)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        learning_rate=3e-4,
        ent_coef=0.01,
        clip_range=0.2,
        tensorboard_log=None,
    )

    logger.info("Training PPO agent for %d timesteps …", total_timesteps)
    model.learn(total_timesteps=total_timesteps, progress_bar=False)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_PATH))
    logger.info("RL agent saved to %s", MODEL_PATH)

    # Evaluate
    obs, _ = env.reset()
    total_reward = 0.0
    for _ in range(365):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _, _ = env.step(action)
        total_reward += reward
        if done:
            break

    return {"total_timesteps": total_timesteps, "eval_reward": round(total_reward, 2)}


def rl_recommend_order(
    stock_level: float,
    forecast_mean: float,
    forecast_p90: float,
    risk_score: float,
    pending_orders: float,
    unit_cost: float,
    eoq: float = 500.0,
) -> float:
    """
    Use trained PPO agent to recommend order quantity.
    Falls back to statistical policy if model not available.
    """
    if not MODEL_PATH.exists():
        logger.warning("RL model not trained, using statistical fallback.")
        return 0.0  # Let reorder_policy handle it

    try:
        from stable_baselines3 import PPO
        model = PPO.load(str(MODEL_PATH))
        obs = np.array([
            min(1.0, stock_level / (eoq * 5)),
            min(1.0, forecast_mean / (eoq * 10)),
            min(1.0, forecast_p90 / (eoq * 10)),
            risk_score / 100.0,
            min(1.0, pending_orders / (eoq * 5)),
            min(1.0, unit_cost / 5000.0),
        ], dtype=np.float32)

        action, _ = model.predict(obs, deterministic=True)
        order_qty = max(0.0, float(action[0]) * eoq)
        return round(order_qty, 0)
    except Exception as exc:
        logger.error("RL inference error: %s", exc)
        return 0.0
