"""High-level HexaLoam robot controller API for single-ESP32, dual-ESP32, and simulation."""
from __future__ import annotations

import numpy as np

from hexaloam_controller.configuration.loader import load_robot_config
from hexaloam_controller.hardware.actuator_bus import UnifiedActuatorBus
from hexaloam_controller.kinematics.hexapod_kinematics import HexaLoamKinematics
from hexaloam_controller.locomotion.gait_engine import GaitEngine


class HexaLoamRobot:
    """Unified high-level interface matching Section 28 specification."""

    def __init__(self, mode: str = "mock_single", ports: tuple[str, ...] = (), baud: int = 460800) -> None:
        self.config = load_robot_config()
        self.kinematics = HexaLoamKinematics(self.config)
        self.gait = GaitEngine(self.kinematics)
        self.bus = UnifiedActuatorBus(mode=mode, ports=ports, baud=baud)
        self.connected = False
        self.armed = False

    def connect(self) -> None:
        self.bus.connect()
        self.connected = True

    def disconnect(self) -> None:
        if self.armed:
            self.disarm()
        self.bus.disconnect()
        self.connected = False

    def validate_configuration(self) -> bool:
        joints = self.config["joints"]
        if len(joints) != 18:
            raise ValueError("Canonical config must define exactly 18 joints")
        expected_ids = list(range(18))
        if [j["id"] for j in joints] != expected_ids:
            raise ValueError("Joint IDs must be contiguous 0..17")
        return True

    def arm(self) -> None:
        self.bus.arm()
        self.armed = True

    def disarm(self) -> None:
        self.bus.disarm()
        self.armed = False

    def stand(self, body_height_m: float | None = None) -> np.ndarray:
        if body_height_m is not None:
            self.set_body_height(body_height_m)
        feet = self.kinematics.default_standing_feet(self.gait.body_height_m)
        q = self.kinematics.whole_body_ik(feet, clamp_workspace=True)
        self.bus.send_joints(q)
        return q

    def sit(self) -> np.ndarray:
        return self.stand(body_height_m=0.085)

    def set_gait(self, gait_name: str) -> None:
        self.gait.set_gait(gait_name)

    def set_body_height(self, height_m: float) -> None:
        if not 0.07 <= height_m <= 0.21:
            raise ValueError(f"Body height {height_m:.3f} m out of safe range [0.07, 0.21] m")
        self.gait.body_height_m = float(height_m)

    def move(self, vx: float = 0.03, vy: float = 0.0, wz: float = 0.0, dt: float = 0.02) -> np.ndarray:
        q, _, _ = self.gait.step(dt=dt, vx=vx, vy=vy, wz=wz)
        self.bus.send_joints(q)
        return q

    def stop(self) -> np.ndarray:
        return self.stand()
