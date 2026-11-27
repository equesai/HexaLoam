# HexaLoam Electronics Bill of Materials (BOM)

| Category | Component | Qty (Max Config) | Notes |
|---|---|---:|---|
| Actuators | MG996R Metal-Gear Servo | 36 (2 per joint × 18 joints) | Back-to-back mirrored `MA1`/`MA2` pairs; center both at `1500 us` (90°) before coupling; verify wire color pinout |
| Controller (Config A) | Arduino Mega 2560 | 1 | D22–D39 direct PWM |
| Controller (Config B/C/D) | ESP32 DevKit (30/38-pin) | 1–2 | GPIO21 SDA, GPIO22 SCL |
| PWM Driver | PCA9685 16-Ch 12-bit Module | 2 | 0x40 (default), 0x41 (A0 jumper) |
| Compute (Config C/D) | Raspberry Pi 4 or 5 (4GB+) | 1 | USB Serial + RP-Lidar + ROS2 |
| LiDAR | Slamtec RP-Lidar A1/A2 | 1 | Mounted on `-Z` underside |
| Power | 6.0V 35A+ (or 2× 20A) Buck + 5.0V 5A Buck | 1 set | Separate 6V actuator & 5V logic rails |
| Battery | 3S 5000 mAh 30C–50C LiPo (~360 g) | 1 | 11.1 V nominal, 12.6 V max, XT60 |
| Protection | 40A Main Fuse + 2× 20A Branch + NC E-Stop | 1 set | Hardware power isolation |
| Signal Reverser | Inline PWM Servo Signal Reverser (for MA2) | 18 | Mirrors back-to-back MA2 from the 18-ch bus (one per joint; MA2 = 3000 - MA1 us) |
| Battery Sense | 33 kΩ + 10 kΩ 1% resistors, 100 nF capacitor | 1 set | 3S battery divider, x4.3 scale, 2.93 V at 12.6 V |
| Bulk Cap | 4700 uF 16V Low-ESR Electrolytic | 2 | Across servo power buses |
