"""CAD-derived forward and inverse kinematics for the HexaLoam 18-DOF hexapod.

All dimensions come from control/robot-configuration/hexaloam_config.json
(extracted from simulation/cad-export/Full_Robot_Assembly.xml).
ROS/robotics frame: +X forward, +Y left, +Z up.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from hexaloam_controller.configuration.loader import get_joint_specs, get_leg_mounts, load_robot_config

LEG_ORDER = ("LF", "LM", "LR", "RF", "RM", "RR")


@dataclass(frozen=True)
class LinkDimensions:
    coxa_radial_m: float
    coxa_vertical_rise_m: float
    femur_m: float
    tibia_m: float
    foot_radius_m: float


class HexaLoamKinematics:
    """Analytical 3R leg FK/IK and whole-body pose transformation engine."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or load_robot_config()
        links = self.config["cad_geometry"]["links"]
        self.links = LinkDimensions(
            coxa_radial_m=float(links["coxa"]["radial_length_m"]),
            coxa_vertical_rise_m=float(links["coxa"]["vertical_rise_from_yaw_shaft_m"]),
            femur_m=float(links["femur"]["length_m"]),
            tibia_m=float(links["tibia"]["length_m"]),
            foot_radius_m=float(links["tibia"]["foot_sphere_radius_m"]),
        )
        self.mounts = get_leg_mounts(self.config)
        self.joints = get_joint_specs(self.config)
        limits = self.config["joint_limits"]
        self.coxa_limits = (float(limits["coxa"]["min_rad"]), float(limits["coxa"]["max_rad"]))
        self.femur_limits = (float(limits["femur"]["min_rad"]), float(limits["femur"]["max_rad"]))
        self.tibia_limits = (float(limits["tibia"]["min_rad"]), float(limits["tibia"]["max_rad"]))

    def leg_mount_origin(self, leg: str) -> np.ndarray:
        m = self.mounts[leg]
        return np.array([
            m.mount_radius_m * math.cos(m.mount_angle_rad),
            m.mount_radius_m * math.sin(m.mount_angle_rad),
            m.hip_yaw_z_offset_m,
        ], dtype=float)

    def body_to_leg_frame(self, leg: str, p_body: np.ndarray) -> np.ndarray:
        """Transform a 3D point from body frame to leg-local frame (origin at hip yaw)."""
        m = self.mounts[leg]
        rel = np.asarray(p_body, dtype=float) - self.leg_mount_origin(leg)
        c, s = math.cos(-m.mount_angle_rad), math.sin(-m.mount_angle_rad)
        return np.array([c * rel[0] - s * rel[1], s * rel[0] + c * rel[1], rel[2]], dtype=float)

    def leg_to_body_frame(self, leg: str, p_leg: np.ndarray) -> np.ndarray:
        """Transform a 3D point from leg-local frame to body frame."""
        m = self.mounts[leg]
        c, s = math.cos(m.mount_angle_rad), math.sin(m.mount_angle_rad)
        rotated = np.array([c * p_leg[0] - s * p_leg[1], s * p_leg[0] + c * p_leg[1], p_leg[2]], dtype=float)
        return rotated + self.leg_mount_origin(leg)

    def forward_kinematics_leg(self, q_coxa: float, q_femur: float, q_tibia: float) -> np.ndarray:
        """Compute foot sphere center [x, y, z] in leg-local frame from (coxa, femur, tibia) rad."""
        r = (
            self.links.coxa_radial_m
            + self.links.femur_m * math.cos(q_femur)
            + self.links.tibia_m * math.cos(q_femur + q_tibia)
        )
        z = (
            self.links.coxa_vertical_rise_m
            + self.links.femur_m * math.sin(q_femur)
            + self.links.tibia_m * math.sin(q_femur + q_tibia)
        )
        return np.array([r * math.cos(q_coxa), r * math.sin(q_coxa), z], dtype=float)

    def inverse_kinematics_leg(
        self,
        target_leg: Iterable[float],
        elbow_up: bool = True,
        clamp_workspace: bool = False,
    ) -> tuple[float, float, float]:
        """Solve 3R leg IK in leg-local frame. Raises ValueError if unreachable unless clamp_workspace=True."""
        px, py, pz = [float(v) for v in target_leg]
        q_coxa = math.atan2(py, px)
        r_horiz = math.hypot(px, py)
        r_eff = r_horiz - self.links.coxa_radial_m
        z_eff = pz - self.links.coxa_vertical_rise_m

        l2, l3 = self.links.femur_m, self.links.tibia_m
        d_sq = r_eff * r_eff + z_eff * z_eff
        d = math.sqrt(d_sq)
        max_reach = l2 + l3 - 1e-6
        min_reach = abs(l2 - l3) + 1e-6

        if d > max_reach or d < min_reach:
            if not clamp_workspace:
                raise ValueError(f"Unreachable leg target (d={d:.4f} m, valid [{min_reach:.4f}, {max_reach:.4f}])")
            d_clamped = min(max(d, min_reach), max_reach)
            scale = d_clamped / max(d, 1e-9)
            r_eff *= scale
            z_eff *= scale
            d_sq = r_eff * r_eff + z_eff * z_eff

        cos_knee = (d_sq - l2 * l2 - l3 * l3) / (2.0 * l2 * l3)
        cos_knee = min(1.0, max(-1.0, cos_knee))
        q_tibia = -math.acos(cos_knee) if elbow_up else math.acos(cos_knee)
        q_femur = math.atan2(z_eff, r_eff) - math.atan2(l3 * math.sin(q_tibia), l2 + l3 * math.cos(q_tibia))

        self.check_joint_limits(q_coxa, q_femur, q_tibia, raise_on_violation=not clamp_workspace)
        if clamp_workspace:
            q_coxa = min(max(q_coxa, self.coxa_limits[0]), self.coxa_limits[1])
            q_femur = min(max(q_femur, self.femur_limits[0]), self.femur_limits[1])
            q_tibia = min(max(q_tibia, self.tibia_limits[0]), self.tibia_limits[1])
        return (q_coxa, q_femur, q_tibia)

    def check_joint_limits(self, q_coxa: float, q_femur: float, q_tibia: float, raise_on_violation: bool = True) -> bool:
        ok = (
            self.coxa_limits[0] <= q_coxa <= self.coxa_limits[1]
            and self.femur_limits[0] <= q_femur <= self.femur_limits[1]
            and self.tibia_limits[0] <= q_tibia <= self.tibia_limits[1]
        )
        if not ok and raise_on_violation:
            raise ValueError(f"Joint limit exceeded: coxa={q_coxa:.3f}, femur={q_femur:.3f}, tibia={q_tibia:.3f}")
        return ok

    @staticmethod
    def rotation_matrix_rpy(roll: float, pitch: float, yaw: float) -> np.ndarray:
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
        ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
        rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
        return rz @ ry @ rx

    def whole_body_ik(
        self,
        foot_targets_world: dict[str, np.ndarray],
        body_pos: Iterable[float] = (0.0, 0.0, 0.0),
        body_rpy: Iterable[float] = (0.0, 0.0, 0.0),
        clamp_workspace: bool = False,
    ) -> np.ndarray:
        """Compute 18-element joint array [rad] given world foot targets and body pose."""
        pos = np.asarray(list(body_pos), dtype=float)
        r_mat = self.rotation_matrix_rpy(*[float(a) for a in body_rpy])
        r_inv = r_mat.T
        q_all = np.zeros(18, dtype=float)
        for idx, leg in enumerate(LEG_ORDER):
            p_body = r_inv @ (np.asarray(foot_targets_world[leg], dtype=float) - pos)
            p_leg = self.body_to_leg_frame(leg, p_body)
            q_all[idx * 3 : idx * 3 + 3] = self.inverse_kinematics_leg(p_leg, clamp_workspace=clamp_workspace)
        return q_all

    def default_standing_feet(self, body_height_m: float | None = None) -> dict[str, np.ndarray]:
        h = float(body_height_m or self.config["gaits"]["default_body_height_m"])
        r_foot = float(self.config["gaits"]["default_standing_foot_radius_m"])
        z_foot = -h + self.links.foot_radius_m
        feet: dict[str, np.ndarray] = {}
        for leg in LEG_ORDER:
            ang = self.mounts[leg].mount_angle_rad
            feet[leg] = np.array([r_foot * math.cos(ang), r_foot * math.sin(ang), z_foot], dtype=float)
        return feet
