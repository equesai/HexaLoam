"""Automated verification suite for HexaLoam kinematics, gaits, protocol, URDF, and dual-ESP32 safety."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from hexaloam_controller.communication.protocol import (
    CmdId,
    Packet,
    decode_packet,
    decode_set_joints_payload,
    encode_packet,
    encode_set_joints,
)
from hexaloam_controller.configuration.loader import REPO_ROOT, load_robot_config
from hexaloam_controller.kinematics.hexapod_kinematics import LEG_ORDER, HexaLoamKinematics
from hexaloam_controller.locomotion.gait_engine import GaitEngine
from hexaloam_controller.robot import HexaLoamRobot
from hexaloam_controller.simulation.torque_mass_analysis import analyze_all_configurations


def test_canonical_config_and_urdf_consistency() -> None:
    cfg = load_robot_config()
    joints = cfg["joints"]
    assert len(joints) == 18
    assert [j["id"] for j in joints] == list(range(18))

    urdf = ET.parse(REPO_ROOT / "simulation" / "urdf" / "hexaloam.urdf")
    urdf_joints = {el.attrib["name"] for el in urdf.findall(".//joint[@type='revolute']")}
    assert urdf_joints == {j["name"] for j in joints}


def test_fk_ik_roundtrip_and_limits() -> None:
    kin = HexaLoamKinematics()
    feet = kin.default_standing_feet()
    q_all = kin.whole_body_ik(feet)
    assert q_all.shape == (18,)
    for idx, leg in enumerate(LEG_ORDER):
        q_leg = q_all[idx * 3 : idx * 3 + 3]
        p_leg_fk = kin.forward_kinematics_leg(*q_leg)
        p_body_fk = kin.leg_to_body_frame(leg, p_leg_fk)
        assert np.allclose(p_body_fk, feet[leg], atol=1e-5)

    with pytest.raises(ValueError):
        kin.inverse_kinematics_leg([2.0, 0.0, 0.0], clamp_workspace=False)


def test_protocol_encode_decode_and_corruption() -> None:
    targets = [0.1 * (i - 9) for i in range(18)]
    frame = encode_set_joints(controller_id=1, seq=42, angles_rad=targets, exec_time_ms=12345)
    pkt = decode_packet(frame)
    assert pkt.controller_id == 1
    assert pkt.seq == 42
    assert pkt.cmd_id == CmdId.SET_JOINTS
    exec_ms, decoded = decode_set_joints_payload(pkt.payload)
    assert exec_ms == 12345
    assert np.allclose(decoded, targets, atol=1e-3)

    corrupted = bytearray(frame)
    corrupted[-1] ^= 0xFF
    with pytest.raises(ValueError, match="CRC mismatch"):
        decode_packet(bytes(corrupted))

    hello = encode_packet(Packet(controller_id=2, seq=1, cmd_id=CmdId.HELLO))
    assert decode_packet(hello).cmd_id == CmdId.HELLO


@pytest.mark.parametrize("gait_name,min_stance", [("tripod", 3), ("ripple", 4), ("wave", 5)])
def test_gaits_continuity_and_support(gait_name: str, min_stance: int) -> None:
    engine = GaitEngine()
    engine.set_gait(gait_name)
    prev_q = None
    for step_idx in range(100):
        q, _, stance = engine.step(dt=0.05, vx=0.03)
        assert q.shape == (18,)
        assert sum(1 for v in stance.values() if v) >= min_stance
        if prev_q is not None:
            assert np.max(np.abs(q - prev_q)) < 0.35
        prev_q = q


def test_robot_single_and_dual_controller_safe_stop() -> None:
    for mode in ("mock_single", "mock_dual"):
        robot = HexaLoamRobot(mode=mode)
        robot.connect()
        assert robot.validate_configuration()
        robot.arm()
        robot.stand()
        robot.set_gait("tripod")
        robot.move(vx=0.03)
        robot.set_gait("ripple")
        robot.set_body_height(0.15)
        robot.stop()
        robot.sit()
        robot.disarm()
        robot.disconnect()

    dual = HexaLoamRobot(mode="mock_dual")
    dual.connect()
    dual.arm()
    dual.bus._mocks[2].fail_next = True
    with pytest.raises(TimeoutError):
        dual.move(vx=0.03)
    # Verify both controllers transitioned to disarmed/estop safe state
    assert not dual.bus._mocks[1].armed
    assert dual.bus._mocks[1].estop


def test_torque_and_mass_analysis_all_configs() -> None:
    res = analyze_all_configurations()
    assert set(res.keys()) == {"A_arduino_mega", "B_esp32_standalone", "C_rpi_single_esp32", "D_rpi_dual_esp32"}
    for item in res.values():
        assert item["total_mass_kg"] > 5.0
        assert item["tripod_3leg_peak_torque_nm"]["femur"] > 0.0
