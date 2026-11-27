"""Drift guard: config, URDF, firmware header and generated wiring files must keep telling the same story."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from hexaloam_controller.configuration.loader import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "control" / "robot-configuration" / "hexaloam_config.json"
URDF_PATH = REPO_ROOT / "simulation" / "urdf" / "hexaloam.urdf"
HEADER_PATH = REPO_ROOT / "firmware" / "shared" / "hexaloam_joint_map.h"
TOL = 1e-5


@pytest.fixture(scope="module")
def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def urdf_joints() -> dict:
    root = ET.parse(URDF_PATH).getroot()
    out = {}
    for el in root.findall("joint"):
        if el.attrib.get("type") != "revolute":
            continue
        limit = el.find("limit")
        out[el.attrib["name"]] = {
            "min": float(limit.attrib["lower"]),
            "max": float(limit.attrib["upper"]),
            "effort": float(limit.attrib["effort"]),
            "origin": [float(v) for v in el.find("origin").attrib["xyz"].split()],
        }
    return out


@pytest.fixture(scope="module")
def header_joints() -> dict:
    text = HEADER_PATH.read_text(encoding="utf-8")
    pat = re.compile(r'\{(\d+), "(\w+)", \d+, \'[AB]\', 0x[0-9A-Fa-f]+, 0x[0-9A-Fa-f]+, \d+, -?\d+, '
                     r'(-?[\d.]+)f, (-?[\d.]+)f, (-?[\d.]+)f\}')
    return {m.group(2): {"min": float(m.group(3)), "max": float(m.group(4)), "neutral": float(m.group(5))}
            for m in pat.finditer(text)}


def test_joint_limits_agree_between_config_urdf_and_firmware(config, urdf_joints, header_joints) -> None:
    assert len(config["joints"]) == len(urdf_joints) == len(header_joints) == 18
    for joint in config["joints"]:
        name = joint["name"]
        top = config["joint_limits"][joint["joint"]]
        for source, lo, hi in (
            ("top-level config", top["min_rad"], top["max_rad"]),
            ("urdf", urdf_joints[name]["min"], urdf_joints[name]["max"]),
            ("firmware header", header_joints[name]["min"], header_joints[name]["max"]),
        ):
            assert lo == pytest.approx(joint["min_rad"], abs=TOL), f"{name} min differs in {source}"
            assert hi == pytest.approx(joint["max_rad"], abs=TOL), f"{name} max differs in {source}"
        assert header_joints[name]["neutral"] == pytest.approx(joint["neutral_rad"], abs=TOL)
        assert top["neutral_rad"] == pytest.approx(joint["neutral_rad"], abs=TOL)


def test_link_lengths_agree_between_config_urdf_and_firmware(config) -> None:
    links = config["cad_geometry"]["links"]
    header = HEADER_PATH.read_text(encoding="utf-8")

    def const(name: str) -> float:
        return float(re.search(rf"{name}\s*=\s*(-?[\d.]+)f", header).group(1))

    assert const("COXA_LENGTH_M") == pytest.approx(links["coxa"]["radial_length_m"], abs=TOL)
    assert const("COXA_LATERAL_OFFSET_M") == pytest.approx(links["coxa"]["lateral_offset_m"], abs=TOL)
    assert const("COXA_VERTICAL_RISE_M") == pytest.approx(links["coxa"]["vertical_rise_from_yaw_shaft_m"], abs=TOL)
    assert const("FEMUR_LENGTH_M") == pytest.approx(links["femur"]["length_m"], abs=TOL)
    assert const("TIBIA_LENGTH_M") == pytest.approx(links["tibia"]["length_m"], abs=TOL)
    assert const("TIBIA_LATERAL_OFFSET_M") == pytest.approx(links["tibia"]["lateral_offset_m"], abs=TOL)

    root = ET.parse(URDF_PATH).getroot()
    joints = {el.attrib["name"]: el for el in root.findall("joint")}
    link_els = {el.attrib["name"]: el for el in root.findall("link")}
    for leg in ("LF", "LM", "LR", "RF", "RM", "RR"):
        femur = [float(v) for v in joints[f"{leg}_FEMUR"].find("origin").attrib["xyz"].split()]
        tibia = [float(v) for v in joints[f"{leg}_TIBIA"].find("origin").attrib["xyz"].split()]
        box = link_els[f"{leg}_tibia_link"].find("visual/geometry/box").attrib["size"].split()
        assert femur[0] == pytest.approx(links["coxa"]["radial_length_m"], abs=TOL), leg
        assert femur[2] == pytest.approx(links["coxa"]["vertical_rise_from_yaw_shaft_m"], abs=TOL), leg
        assert abs(femur[1]) == pytest.approx(abs(links["coxa"]["lateral_offset_m"]), abs=TOL), leg
        assert tibia[0] == pytest.approx(links["femur"]["length_m"], abs=TOL), leg
        assert float(box[0]) == pytest.approx(links["tibia"]["length_m"], abs=TOL), leg


def test_urdf_effort_is_two_servos_at_stall(config, urdf_joints) -> None:
    servo = config["servo_actuator"]
    assert config["cad_geometry"]["chassis"]["servos_per_joint"] == 2
    expected = 2 * servo["stall_torque_6v0_nm"]
    for name, joint in urdf_joints.items():
        assert joint["effort"] == pytest.approx(expected, abs=2e-3), name


def test_servo_count_is_36(config) -> None:
    chassis = config["cad_geometry"]["chassis"]
    assert chassis["total_servos"] == 36
    assert chassis["total_servos"] == chassis["servos_per_joint"] * config["robot"]["dof"]


def test_total_cad_mass_counts_all_36_servos(config) -> None:
    chassis = config["cad_geometry"]["chassis"]
    legs = sum(chassis["mass_per_leg_links_kg"].values()) * config["robot"]["legs"]
    total = (chassis["mass_robot_base_kg"] + chassis["mass_lidar_cover_kg"] + chassis["mass_rplidar_kg"]
             + legs + chassis["total_servos"] * chassis["mass_per_servo_cad_kg"])
    assert chassis["total_printed_and_servo_cad_mass_kg"] == pytest.approx(total, abs=1e-4)


def test_no_generated_wiring_file_says_18_mg996r() -> None:
    pattern = re.compile(r"\b18\s*[x×]?\s*MG996R", re.IGNORECASE)
    offenders = []
    for folder in ("wiring", "connection-tables", "schematics", "bom", "power"):
        for path in (REPO_ROOT / "electronics" / folder).rglob("*"):
            if path.suffix.lower() in {".svg", ".md", ".json"} and pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    gen = (REPO_ROOT / "electronics" / "generate_wiring_diagrams.py").read_text(encoding="utf-8")
    if pattern.search(gen):
        offenders.append("electronics/generate_wiring_diagrams.py")
    assert not offenders, offenders
