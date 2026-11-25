# HexaLoam Electronics Bill of Materials (BOM)

| Category | Component | Qty (Max Config) | Notes |
|---|---|---:|---|
| Actuators | MG996R Metal-Gear Servo | 18 | Verify wire color pinout before plugging |
| Controller (Config A) | Arduino Mega 2560 | 1 | D22–D39 direct PWM |
| Controller (Config B/C/D) | ESP32 DevKit (30/38-pin) | 1–2 | GPIO21 SDA, GPIO22 SCL |
| PWM Driver | PCA9685 16-Ch 12-bit Module | 2 | 0x40 (default), 0x41 (A0 jumper) |
| Compute (Config C/D) | Raspberry Pi 4 or 5 (4GB+) | 1 | USB Serial + RP-Lidar + ROS2 |
| LiDAR | Slamtec RP-Lidar A1/A2 | 1 | Mounted on `-Z` underside |
| Power | 6.0V 25A+ Buck + 5.0V 5A Buck | 1 each | Separate actuator & logic rails |
| Protection | 30A Main Fuse + 2x 15A Branch + NC E-Stop | 1 set | Hardware power isolation |
| Bulk Cap | 4700 uF 16V Low-ESR Electrolytic | 2 | Across servo power buses |
