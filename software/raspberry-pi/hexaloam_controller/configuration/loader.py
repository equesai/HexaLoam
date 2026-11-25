"""Canonical configuration and calibration loader for HexaLoam."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = REPO_ROOT / "control" / "robot-configuration" / "hexaloam_config.json"
DEFAULT_CALIBRATION_PATH = REPO_ROOT / "control" / "calibration" / "default_calibration.json"


@dataclass(frozen=True)
class LegMount:
    leg: str
    side: str
    mount_angle_rad: float
    mount_radius_m: float
    hip_yaw_z_offset_m: float


@dataclass(frozen=True)
class JointSpec:
    id: int
    name: str
    leg: str
    joint: str
    side: str
    pca_board: str
    pca_channel: int
    direction: int
    min_rad: float
    max_rad: float
    neutral_rad: float


def load_robot_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def load_calibration(path: Path | None = None) -> dict[str, Any]:
    cal_path = path or DEFAULT_CALIBRATION_PATH
    return json.loads(cal_path.read_text(encoding="utf-8"))


def get_leg_mounts(cfg: dict[str, Any] | None = None) -> dict[str, LegMount]:
    data = cfg or load_robot_config()
    mounts: dict[str, LegMount] = {}
    for m in data["cad_geometry"]["leg_mounts"]:
        mounts[m["leg"]] = LegMount(
            leg=m["leg"],
            side=m["side"],
            mount_angle_rad=float(m["mount_angle_rad"]),
            mount_radius_m=float(m["mount_radius_m"]),
            hip_yaw_z_offset_m=float(m["hip_yaw_z_offset_m"]),
        )
    return mounts


def get_joint_specs(cfg: dict[str, Any] | None = None) -> list[JointSpec]:
    data = cfg or load_robot_config()
    return [
        JointSpec(
            id=int(j["id"]),
            name=j["name"],
            leg=j["leg"],
            joint=j["joint"],
            side=j["side"],
            pca_board=j["pca_board"],
            pca_channel=int(j["pca_channel"]),
            direction=int(j["direction"]),
            min_rad=float(j["min_rad"]),
            max_rad=float(j["max_rad"]),
            neutral_rad=float(j["neutral_rad"]),
        )
        for j in data["joints"]
    ]
