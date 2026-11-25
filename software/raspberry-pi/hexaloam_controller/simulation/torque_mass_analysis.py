"""Compute mass budget and analytical 3R joint holding torques for Configs A, B, C, and D.

Uses exact CAD link/chassis masses from Full_Robot_Assembly.xml and analytical
Jacobian J^T * F at neutral standing and worst-case 3-leg tripod stance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from hexaloam_controller.configuration.loader import REPO_ROOT, load_robot_config
from hexaloam_controller.kinematics.hexapod_kinematics import HexaLoamKinematics

GRAVITY = 9.80665


def leg_jacobian_local(kin: HexaLoamKinematics, q_coxa: float, q_femur: float, q_tibia: float) -> np.ndarray:
    """Analytical 3x3 linear Jacobian dp_leg / dq for [coxa, femur, tibia]."""
    l1 = kin.links.coxa_radial_m
    l2 = kin.links.femur_m
    l3 = kin.links.tibia_m
    r = l1 + l2 * math.cos(q_femur) + l3 * math.cos(q_femur + q_tibia)
    dr_df = -l2 * math.sin(q_femur) - l3 * math.sin(q_femur + q_tibia)
    dr_dt = -l3 * math.sin(q_femur + q_tibia)
    dz_df = l2 * math.cos(q_femur) + l3 * math.cos(q_femur + q_tibia)
    dz_dt = l3 * math.cos(q_femur + q_tibia)
    c, s = math.cos(q_coxa), math.sin(q_coxa)
    return np.array([
        [-r * s, c * dr_df, c * dr_dt],
        [r * c,  s * dr_df, s * dr_dt],
        [0.0,    dz_df,     dz_dt],
    ], dtype=float)


def analyze_all_configurations() -> dict:
    cfg = load_robot_config()
    kin = HexaLoamKinematics(cfg)
    base_mass_kg = float(cfg["cad_geometry"]["chassis"]["total_printed_and_servo_physical_est_kg"])
    stall_nm = float(cfg["servo_actuator"]["stall_torque_6v0_nm"])

    feet = kin.default_standing_feet()
    q_stand = kin.whole_body_ik(feet)
    q_lf = q_stand[0:3]
    jac = leg_jacobian_local(kin, *q_lf)

    results = {}
    for key, conf in cfg["control_configurations"].items():
        payload_kg = sum(float(v) for v in conf["top_payload_components_kg"].values())
        total_kg = base_mass_kg + payload_kg
        weight_n = total_kg * GRAVITY

        # 6-leg equal stance vs 3-leg tripod worst-case stance (with 1.25 dynamic factor)
        fz_6 = weight_n / 6.0
        fz_3 = (weight_n / 3.0) * 1.25
        tau_6 = np.abs(jac.T @ np.array([0.0, 0.0, -fz_6]))
        tau_3 = np.abs(jac.T @ np.array([0.0, 0.0, -fz_3]))

        results[key] = {
            "name": conf["name"],
            "base_structure_and_servos_kg": round(base_mass_kg, 3),
            "top_controllers_and_battery_kg": round(payload_kg, 3),
            "total_mass_kg": round(total_kg, 3),
            "total_weight_n": round(weight_n, 2),
            "six_leg_stance_torque_nm": {"coxa": round(float(tau_6[0]), 3), "femur": round(float(tau_6[1]), 3), "tibia": round(float(tau_6[2]), 3)},
            "tripod_3leg_peak_torque_nm": {"coxa": round(float(tau_3[0]), 3), "femur": round(float(tau_3[1]), 3), "tibia": round(float(tau_3[2]), 3)},
            "mg996r_stall_torque_6v_nm": stall_nm,
            "femur_utilization_tripod_pct": round(100.0 * float(tau_3[1]) / stall_nm, 1),
            "tibia_utilization_tripod_pct": round(100.0 * float(tau_3[2]) / stall_nm, 1),
        }
    return results


if __name__ == "__main__":
    out = analyze_all_configurations()
    out_path = REPO_ROOT / "control" / "robot-configuration" / "torque_mass_analysis.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
