# HexaLoam Servo Calibration Guide

1. **Bench-center each servo BEFORE mounting horns** using `02_Servo_Calibration.ino` (Arduino Mega) or the ESP32 `CALIBRATE` debug command (`1500 us` neutral).
2. **Verify direction signs:** Left-side joints (`0..8`) default to `+1`; right-side joints (`9..17`) default to `-1` for mirrored servo mounting. Always test with a single leg elevated before assembling all 6 legs.
3. **Record zero offsets and safe pulse bounds:** Update `default_calibration.json` (or persist to ESP32 NVS `Preferences`) and verify physical travel limits do not collide with the chassis or adjacent links.
