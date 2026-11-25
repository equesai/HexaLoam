"""Binary & JSON communication protocol codec for HexaLoam ESP32 actuator slaves."""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

SYNC_BYTES = b"\xAA\x55"
PROTOCOL_VERSION = 1
MAX_PACKET_BYTES = 256


class CmdId(IntEnum):
    HELLO = 0x01
    GET_VERSION = 0x02
    GET_CAPABILITIES = 0x03
    GET_CONFIGURATION = 0x04
    SET_CONFIGURATION = 0x05
    ARM = 0x10
    DISARM = 0x11
    SET_JOINT = 0x12
    SET_JOINTS = 0x13
    SET_TRAJECTORY = 0x14
    SET_SPEED_LIMIT = 0x15
    SET_ACCELERATION_LIMIT = 0x16
    SET_NEUTRAL_POSE = 0x17
    GET_STATUS = 0x20
    GET_SENSOR_DATA = 0x21
    GET_POWER_STATUS = 0x22
    CALIBRATE = 0x23
    HEARTBEAT = 0x30
    EMERGENCY_STOP = 0x40
    CLEAR_FAULT = 0x41
    SYNC_TIME = 0x50
    ACK = 0x80
    NACK = 0x81
    FAULT = 0x82
    TELEMETRY = 0x83


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    """Compute CRC-16/CCITT-FALSE over data."""
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else ((crc << 1) & 0xFFFF)
    return crc


@dataclass(frozen=True)
class Packet:
    controller_id: int
    seq: int
    cmd_id: CmdId
    payload: bytes = b""
    version: int = PROTOCOL_VERSION


def encode_packet(pkt: Packet) -> bytes:
    if len(pkt.payload) + 11 > MAX_PACKET_BYTES:
        raise ValueError("Payload exceeds MAX_PACKET_BYTES")
    body = struct.pack(
        "<BBHBH",
        pkt.version,
        pkt.controller_id,
        pkt.seq & 0xFFFF,
        int(pkt.cmd_id),
        len(pkt.payload),
    ) + pkt.payload
    crc = crc16_ccitt(body)
    return SYNC_BYTES + body + struct.pack("<H", crc)


def decode_packet(frame: bytes) -> Packet:
    if len(frame) < 11 or frame[:2] != SYNC_BYTES:
        raise ValueError("Invalid frame header or length")
    version, ctrl_id, seq, cmd_raw, length = struct.unpack("<BBHBH", frame[2:9])
    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version {version}")
    expected_total = 2 + 7 + length + 2
    if len(frame) != expected_total:
        raise ValueError(f"Length mismatch: got {len(frame)}, expected {expected_total}")
    payload = frame[9 : 9 + length]
    crc_rx = struct.unpack("<H", frame[9 + length : 11 + length])[0]
    crc_calc = crc16_ccitt(frame[2 : 9 + length])
    if crc_rx != crc_calc:
        raise ValueError(f"CRC mismatch: rx=0x{crc_rx:04X}, calc=0x{crc_calc:04X}")
    return Packet(controller_id=ctrl_id, seq=seq, cmd_id=CmdId(cmd_raw), payload=payload, version=version)


def rad_to_mrad_i16(rad: float) -> int:
    val = int(round(rad * 1000.0))
    return max(-32767, min(32767, val))


def encode_set_joints(
    controller_id: int,
    seq: int,
    angles_rad: Iterable[float],
    exec_time_ms: int = 0,
) -> bytes:
    """Encode SET_JOINTS payload: uint32 exec_time_ms + uint8 count + int16[count] mrad."""
    mrad = [rad_to_mrad_i16(a) for a in angles_rad]
    payload = struct.pack(f"<IB{len(mrad)}h", exec_time_ms & 0xFFFFFFFF, len(mrad), *mrad)
    return encode_packet(Packet(controller_id=controller_id, seq=seq, cmd_id=CmdId.SET_JOINTS, payload=payload))


def decode_set_joints_payload(payload: bytes) -> tuple[int, list[float]]:
    exec_ms, count = struct.unpack("<IB", payload[:5])
    mrad = struct.unpack(f"<{count}h", payload[5 : 5 + 2 * count])
    return exec_ms, [v / 1000.0 for v in mrad]


def encode_debug_json(cmd: str, **kwargs) -> bytes:
    return (json.dumps({"cmd": cmd, **kwargs}, separators=(",", ":")) + "\n").encode("utf-8")
