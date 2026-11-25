"""Generate mirrored MA1/MA2 torque profile diagram for Joints A (Coxa), B (Femur), C (Tibia)."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software" / "raspberry-pi"))

from hexaloam_controller.kinematics.hexapod_kinematics import LEG_ORDER
from hexaloam_controller.locomotion.gait_engine import GaitEngine
from hexaloam_controller.simulation.torque_mass_analysis import GRAVITY, leg_jacobian_local

MASS_CONFIG_C_KG = 3.989  # G-code PLA+ + 36 MG996Rs + RPi + ESP32 + RP-Lidar + 3S 5000mAh LiPo
STALL_PER_MOTOR = 1.0787
SAFE_70_PER_MOTOR = 0.70 * STALL_PER_MOTOR


def simulate_gait_torques(gait_name: str, total_mass_kg: float = MASS_CONFIG_C_KG) -> tuple[np.ndarray, np.ndarray]:
    engine = GaitEngine()
    engine.set_gait(gait_name)
    dt = 0.02
    steps = int(round(engine.gaits[gait_name].cycle_s / dt))
    times = np.arange(steps) * dt
    tau_lf = np.zeros((steps, 3), dtype=float)
    weight_n = total_mass_kg * GRAVITY

    for i in range(steps):
        q, _, stance = engine.step(dt=dt, vx=0.03)
        n_stance = max(1, sum(1 for v in stance.values() if v))
        fz = -(weight_n / n_stance) if stance["LF"] else -2.5  # ~0.25 kg leg gravity during swing
        jac = leg_jacobian_local(engine.kin, q[0], q[1], q[2])
        tau_joint = jac.T @ np.array([0.0, 0.0, fz])
        tau_lf[i, :] = tau_joint
    return times, tau_lf


def main() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 8.5), dpi=150)
    gait_list = [("wave", "Wave Gait (5 legs stance)"), ("ripple", "Ripple Gait (4 legs stance)"), ("tripod", "Tripod Gait (3 legs stance)")]

    for ax, (gname, title) in zip(axes, gait_list):
        t, tau_j = simulate_gait_torques(gname)
        # Back-to-back motors share joint load equally with mirrored sign: MA1 = +tau/2, MA2 = -tau/2
        ma1 = tau_j / 2.0
        ma2 = -tau_j / 2.0

        ax.plot(t, ma1[:, 0], color="#0284C7", lw=1.6, label="Joint A (Coxa) MA1 (+)")
        ax.plot(t, ma2[:, 0], color="#0284C7", lw=1.2, ls="--", alpha=0.8, label="Joint A (Coxa) MA2 (-)")
        ax.plot(t, ma1[:, 1], color="#D97706", lw=2.2, label="Joint B (Femur) MA1 (+)")
        ax.plot(t, ma2[:, 1], color="#D97706", lw=1.8, ls="--", alpha=0.85, label="Joint B (Femur) MA2 (-)")
        ax.plot(t, ma1[:, 2], color="#16A34A", lw=1.6, label="Joint C (Tibia) MA1 (+)")
        ax.plot(t, ma2[:, 2], color="#16A34A", lw=1.2, ls="--", alpha=0.8, label="Joint C (Tibia) MA2 (-)")

        ax.axhline(SAFE_70_PER_MOTOR, color="#985107", ls=":", lw=1.2, label="70% Safe Continuous (±0.755 N·m)")
        ax.axhline(-SAFE_70_PER_MOTOR, color="#985107", ls=":", lw=1.2)
        ax.axhline(STALL_PER_MOTOR, color="#DC2626", ls="-.", lw=1.2, label="100% MG996R Stall (±1.079 N·m)")
        ax.axhline(-STALL_PER_MOTOR, color="#DC2626", ls="-.", lw=1.2)
        ax.axhline(0.0, color="#64748B", lw=0.6)

        ax.set_title(f"{title} — Config C ({MASS_CONFIG_C_KG:.3f} kg) Mirrored Back-to-Back Motor Torque (MA1 & MA2)", fontsize=10.5, fontweight="bold")
        ax.set_ylabel("Per-Motor Torque (N·m)")
        ax.set_ylim(-1.25, 1.25)
        ax.grid(True, alpha=0.25)
        if gname == "wave":
            ax.legend(loc="upper right", ncol=4, fontsize=7.2, framealpha=0.92)

        peak_b = float(np.max(np.abs(ma1[:, 1])))
        peak_c = float(np.max(np.abs(ma1[:, 2])))
        print(f"{gname:8s}: peak MA1/MA2 Joint B (Femur) = ±{peak_b:.3f} N·m ({100*peak_b/STALL_PER_MOTOR:.1f}% stall) | Joint C (Tibia) = ±{peak_c:.3f} N·m")

    axes[-1].set_xlabel("Cycle Time (s)")
    fig.suptitle("HexaLoam Mirrored Dual-Motor Torque Profiles (Joints A: Coxa, B: Femur, C: Tibia)", fontsize=12, fontweight="bold", y=0.995)
    fig.tight_layout()

    for out in (ROOT / "demonstrations" / "motor_torque_profile.png", ROOT / "site" / "assets" / "motor_torque_profile.png"):
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved motor_torque_profile.png to demonstrations/ and site/assets/")


if __name__ == "__main__":
    main()
