"""Unified single-ESP32, dual-ESP32, and mock actuator bus for HexaLoam."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from hexaloam_controller.communication.protocol import CmdId, Packet, decode_packet, encode_packet, encode_set_joints

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


@dataclass
class ControllerNode:
    controller_id: int
    port: str
    joint_slice: slice
    baud: int = 460800
    armed: bool = False
    faulted: bool = False
    last_seq: int = 0
    last_joints_rad: np.ndarray = field(default_factory=lambda: np.zeros(0))


class MockTransport:
    """In-memory deterministic controller simulator for CI and offline testing."""

    def __init__(self, controller_id: int, num_joints: int) -> None:
        self.controller_id = controller_id
        self.num_joints = num_joints
        self.armed = False
        self.estop = False
        self.fail_next = False
        self.joints_rad = np.zeros(num_joints, dtype=float)
        self.history: list[Packet] = []

    def exchange(self, frame: bytes) -> Packet:
        if self.fail_next:
            raise TimeoutError(f"Simulated timeout on controller {self.controller_id}")
        pkt = decode_packet(frame)
        self.history.append(pkt)
        if pkt.cmd_id == CmdId.ARM and not self.estop:
            self.armed = True
        elif pkt.cmd_id == CmdId.DISARM:
            self.armed = False
        elif pkt.cmd_id == CmdId.EMERGENCY_STOP:
            self.estop = True
            self.armed = False
        elif pkt.cmd_id == CmdId.CLEAR_FAULT:
            self.estop = False
        elif pkt.cmd_id == CmdId.SET_JOINTS:
            if not self.armed or self.estop:
                return Packet(self.controller_id, pkt.seq, CmdId.NACK, b"\x04")
        return Packet(self.controller_id, pkt.seq, CmdId.ACK, b"")


class UnifiedActuatorBus:
    """Controls 18 DOF over single-ESP32 (1x18), dual-ESP32 (2x9), or mock backend."""

    def __init__(self, mode: str = "mock", ports: tuple[str, ...] = (), baud: int = 460800) -> None:
        if mode not in {"mock_single", "mock_dual", "single_esp32", "dual_esp32", "mock"}:
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = "mock_single" if mode == "mock" else mode
        self.baud = baud
        self._seq = 0
        self._serials: dict[int, object] = {}
        self._mocks: dict[int, MockTransport] = {}

        if self.mode in {"mock_single", "single_esp32"}:
            self.nodes = [ControllerNode(1, ports[0] if ports else "/dev/hexaloam_esp32", slice(0, 18), baud)]
        else:
            p_a = ports[0] if len(ports) > 0 else "/dev/hexaloam_left"
            p_b = ports[1] if len(ports) > 1 else "/dev/hexaloam_right"
            self.nodes = [
                ControllerNode(1, p_a, slice(0, 9), baud),
                ControllerNode(2, p_b, slice(9, 18), baud),
            ]

    def connect(self) -> None:
        for n in self.nodes:
            if self.mode.startswith("mock"):
                n_j = n.joint_slice.stop - n.joint_slice.start
                self._mocks[n.controller_id] = MockTransport(n.controller_id, n_j)
            else:
                if serial is None:
                    raise RuntimeError("pyserial is required for hardware serial connections")
                self._serials[n.controller_id] = serial.Serial(n.port, self.baud, timeout=0.1)
            self._send_cmd(n, CmdId.HELLO)

    def disconnect(self) -> None:
        for ser in self._serials.values():
            ser.close()  # type: ignore[attr-defined]
        self._serials.clear()

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFFFF
        return self._seq

    def _exchange(self, node: ControllerNode, frame: bytes) -> Packet:
        if self.mode.startswith("mock"):
            return self._mocks[node.controller_id].exchange(frame)
        ser = self._serials[node.controller_id]
        ser.write(frame)  # type: ignore[attr-defined]
        hdr = ser.read(9)  # type: ignore[attr-defined]
        if len(hdr) < 9:
            raise TimeoutError(f"Controller {node.controller_id} timed out")
        length = int.from_bytes(hdr[7:9], "little")
        rest = ser.read(length + 2)  # type: ignore[attr-defined]
        return decode_packet(hdr + rest)

    def _send_cmd(self, node: ControllerNode, cmd: CmdId) -> Packet:
        seq = self._next_seq()
        frame = encode_packet(Packet(controller_id=node.controller_id, seq=seq, cmd_id=cmd))
        return self._exchange(node, frame)

    def arm(self) -> None:
        for n in self.nodes:
            resp = self._send_cmd(n, CmdId.ARM)
            if resp.cmd_id != CmdId.ACK:
                raise RuntimeError(f"Controller {n.controller_id} refused ARM")
            n.armed = True

    def disarm(self) -> None:
        for n in self.nodes:
            try:
                self._send_cmd(n, CmdId.DISARM)
            finally:
                n.armed = False

    def emergency_stop_all(self) -> None:
        """Broadcast E-stop to all controllers; never let one failure skip the other."""
        for n in self.nodes:
            n.armed = False
            n.faulted = True
            try:
                self._send_cmd(n, CmdId.EMERGENCY_STOP)
            except Exception:
                pass

    def send_joints(self, q_18_rad: np.ndarray, lead_time_ms: int = 20) -> None:
        if len(q_18_rad) != 18:
            raise ValueError("Expected 18 joint targets")
        exec_ms = int(time.monotonic() * 1000) + lead_time_ms
        seq = self._next_seq()
        try:
            for n in self.nodes:
                sub = q_18_rad[n.joint_slice]
                frame = encode_set_joints(n.controller_id, seq, sub, exec_time_ms=exec_ms)
                resp = self._exchange(n, frame)
                if resp.cmd_id != CmdId.ACK:
                    raise RuntimeError(f"Controller {n.controller_id} returned {resp.cmd_id.name}")
                n.last_joints_rad = sub.copy()
        except Exception:
            # Dual-controller safety: faulted side triggers immediate E-stop on all nodes
            self.emergency_stop_all()
            raise
