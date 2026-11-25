"""Phase-based Tripod, Ripple, and Wave gait generator with cycloidal trajectories."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from hexaloam_controller.kinematics.hexapod_kinematics import LEG_ORDER, HexaLoamKinematics


@dataclass
class GaitConfig:
    name: str
    duty_factor: float
    cycle_s: float
    phase_offsets: dict[str, float]
    stride_m: float = 0.060
    swing_height_m: float = 0.022


class GaitEngine:
    """Generates continuous 6-leg foot trajectories and 18-DOF joint angles."""

    def __init__(self, kinematics: HexaLoamKinematics | None = None) -> None:
        self.kin = kinematics or HexaLoamKinematics()
        gaits_cfg = self.kin.config["gaits"]
        self.gaits: dict[str, GaitConfig] = {}
        for name in ("tripod", "ripple", "wave"):
            g = gaits_cfg[name]
            self.gaits[name] = GaitConfig(
                name=name,
                duty_factor=float(g["duty_factor"]),
                cycle_s=float(g["cycle_s"]),
                phase_offsets={k: float(v) for k, v in g["phase_offsets"].items()},
                stride_m=float(gaits_cfg["default_stride_m"]),
                swing_height_m=float(gaits_cfg["default_swing_height_m"]),
            )
        self.active_gait = "tripod"
        self.phase = 0.0
        self.body_height_m = float(gaits_cfg["default_body_height_m"])

    def set_gait(self, name: str) -> None:
        if name not in self.gaits:
            raise ValueError(f"Unknown gait '{name}'. Supported: {list(self.gaits)}")
        self.active_gait = name

    @staticmethod
    def cycloidal_swing(s: float) -> tuple[float, float]:
        """Return (horizontal_progress in [-0.5, 0.5], vertical_lift_ratio in [0, 1]) for s in [0, 1]."""
        s_clamped = min(max(s, 0.0), 1.0)
        horiz = (s_clamped - math.sin(2.0 * math.pi * s_clamped) / (2.0 * math.pi)) - 0.5
        vert = math.sin(math.pi * s_clamped) ** 2
        return horiz, vert

    def step(
        self,
        dt: float,
        vx: float = 0.03,
        vy: float = 0.0,
        wz: float = 0.0,
        body_rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, bool]]:
        """Advance gait by dt and return (joints_18_rad, foot_targets, is_stance_map)."""
        g = self.gaits[self.active_gait]
        self.phase = (self.phase + dt / g.cycle_s) % 1.0

        neutral_feet = self.kin.default_standing_feet(self.body_height_m)
        speed_norm = math.hypot(vx, vy)
        scale_t = min(1.0, speed_norm / 0.06) if speed_norm > 1e-6 else 0.0
        dir_x = vx / speed_norm if speed_norm > 1e-6 else 1.0
        dir_y = vy / speed_norm if speed_norm > 1e-6 else 0.0

        foot_targets: dict[str, np.ndarray] = {}
        is_stance: dict[str, bool] = {}

        for leg in LEG_ORDER:
            phi = (self.phase - g.phase_offsets[leg]) % 1.0
            swing_dur = 1.0 - g.duty_factor
            base = neutral_feet[leg].copy()

            # Tangential displacement for yaw rotation wz
            rot_x = -base[1] * wz * (g.cycle_s * 0.5)
            rot_y = base[0] * wz * (g.cycle_s * 0.5)

            if phi < swing_dur:
                s = phi / max(swing_dur, 1e-6)
                horiz, vert = self.cycloidal_swing(s)
                is_stance[leg] = False
                lift = g.swing_height_m * vert if (scale_t > 0.0 or abs(wz) > 1e-4) else 0.0
            else:
                s_stance = (phi - swing_dur) / max(g.duty_factor, 1e-6)
                horiz = 0.5 - s_stance
                is_stance[leg] = True
                lift = 0.0

            step_vec = np.array([
                horiz * (g.stride_m * scale_t * dir_x + rot_x),
                horiz * (g.stride_m * scale_t * dir_y + rot_y),
                lift,
            ], dtype=float)
            foot_targets[leg] = base + step_vec

        q_18 = self.kin.whole_body_ik(foot_targets, body_pos=(0.0, 0.0, 0.0), body_rpy=body_rpy, clamp_workspace=True)
        return q_18, foot_targets, is_stance
