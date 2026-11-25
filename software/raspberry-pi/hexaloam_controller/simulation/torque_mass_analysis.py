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
    base_mass_kg = float(cfg["cad_geometry"]["chassis"]["total_printed_and_servo_slicer_est_kg"])
    servos_per_joint = int(cfg["cad_geometry"]["chassis"].get("servos_per_joint", 2))
    stall_nm = float(cfg["servo_actuator"]["stall_torque_6v0_nm"]) * servos_per_joint

    feet = kin.default_standing_feet()
    q_stand = kin.whole_body_ik(feet)
    q_lf = q_stand[0:3]
    jac = leg_jacobian_local(kin, *q_lf)
    tau_per_n = abs(float((jac.T @ np.array([0.0, 0.0, -1.0]))[1]))
    max_wave_70_kg = (0.70 * stall_nm / tau_per_n) * 5.0 / (1.15 * GRAVITY)
    max_ripple_70_kg = (0.70 * stall_nm / tau_per_n) * 4.0 / (1.20 * GRAVITY)
    max_tripod_100_kg = (1.00 * stall_nm / tau_per_n) * 3.0 / (1.25 * GRAVITY)

    results = {}
    for key, conf in cfg["control_configurations"].items():
        payload_kg = sum(float(v) for v in conf["top_payload_components_kg"].values())
        total_kg = base_mass_kg + payload_kg
        weight_n = total_kg * GRAVITY

        fz_6 = weight_n / 6.0
        fz_wave = (weight_n / 5.0) * 1.15
        fz_ripple = (weight_n / 4.0) * 1.20
        fz_3 = (weight_n / 3.0) * 1.25
        tau_6 = np.abs(jac.T @ np.array([0.0, 0.0, -fz_6]))
        tau_wave = np.abs(jac.T @ np.array([0.0, 0.0, -fz_wave]))
        tau_ripple = np.abs(jac.T @ np.array([0.0, 0.0, -fz_ripple]))
        tau_3 = np.abs(jac.T @ np.array([0.0, 0.0, -fz_3]))

        results[key] = {
            "name": conf["name"],
            "base_structure_and_36_servos_kg": round(base_mass_kg, 3),
            "top_controllers_and_3s_lipo_kg": round(payload_kg, 3),
            "total_mass_kg": round(total_kg, 3),
            "total_weight_n": round(weight_n, 2),
            "six_leg_stance_torque_nm": {"coxa": round(float(tau_6[0]), 3), "femur": round(float(tau_6[1]), 3), "tibia": round(float(tau_6[2]), 3)},
            "wave_5leg_torque_nm": round(float(tau_wave[1]), 3),
            "ripple_4leg_torque_nm": round(float(tau_ripple[1]), 3),
            "tripod_3leg_peak_torque_nm": {"coxa": round(float(tau_3[0]), 3), "femur": round(float(tau_3[1]), 3), "tibia": round(float(tau_3[2]), 3)},
            "dual_mg996r_stall_torque_6v_nm": round(stall_nm, 4),
            "femur_utilization_wave_pct": round(100.0 * float(tau_wave[1]) / stall_nm, 1),
            "femur_utilization_ripple_pct": round(100.0 * float(tau_ripple[1]) / stall_nm, 1),
            "femur_utilization_tripod_pct": round(100.0 * float(tau_3[1]) / stall_nm, 1),
            "max_extra_top_payload_wave_70pct_kg": round(max_wave_70_kg - total_kg, 2),
            "max_extra_top_payload_ripple_70pct_kg": round(max_ripple_70_kg - total_kg, 2),
            "max_extra_top_payload_tripod_stall_kg": round(max_tripod_100_kg - total_kg, 2),
        }
    return results


if __name__ == "__main__":
    out = analyze_all_configurations()
    out_path = REPO_ROOT / "control" / "robot-configuration" / "torque_mass_analysis.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
