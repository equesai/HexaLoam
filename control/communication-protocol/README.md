# HexaLoam Standardized Communication Protocol (v1)

The Raspberry Pi and ESP32 actuator controllers communicate over USB Serial using two mutually compatible modes:

1. **Human-Readable Debug Protocol (115200 baud default):** Newline-delimited JSON commands (e.g. `{"cmd":"HELLO"}`, `{"cmd":"ARM"}`, `{"cmd":"SET_JOINT","id":0,"rad":0.0}`, `{"cmd":"EMERGENCY_STOP"}`) for calibration, Serial Monitor debugging, and educational use.
2. **Binary Runtime Protocol (460800 baud recommended):** Compact little-endian framed packets (`[0xAA, 0x55, version, ctrl_id, seq_lo, seq_hi, cmd_id, len_lo, len_hi, payload..., crc_lo, crc_hi]`) using **CRC-16/CCITT-FALSE** and **milliradians (`int16_t`, 1 mrad = 0.001 rad)** so a full 18-joint `SET_JOINTS` packet is **47 bytes** (`~1.02 ms` wire time at 460800 baud vs `~4.08 ms` at 115200 baud), easily sustaining 50–100 Hz control loops on both single- and dual-ESP32 architectures.

See [protocol_spec.json](protocol_spec.json) for the full command table (`HELLO` through `SYNC_TIME`), error codes, and 500 ms watchdog timeout rules.
