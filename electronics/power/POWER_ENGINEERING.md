# HexaLoam Servo Power Supply & Electrical Engineering

## 1. MG996R Electrical & Mechanical Reference Limits (18 Joints × 2 Back-to-Back Motors = 36 Servos)
- **Nominal Operating Voltage:** 4.8 V – 7.2 V (design target: **6.0 V regulated**).
- **Actuator Pairing (`MA1` & `MA2`):** Each of the 18 logical joints uses two opposing back-to-back MG996R servos (`MA1` and `MA2`), centered at `1500 us` (90°) before mechanical coupling and driven with mirrored offsets (`MA1 = 1500 + Δus`, `MA2 = 3000 - MA1`).
  - **18-Channel Mode (Default Config A/B/C/D):** Each logical joint output drives `MA1` directly and `MA2` through an inline **hardware PWM servo signal reverser** (mirrored Y-harness), keeping wiring to 18 channels.
  - **36-Channel Software-Mirrored Mode (Optional):** Use 3× PCA9685 boards (`0x40`, `0x41`, `0x42` = 48 channels) on ESP32 or pins `D22..D57` on Arduino Mega (`Servo.h` supports up to 48 servos) to drive `MA1` and `MA2` on independent firmware-mirrored channels (`radToUsMA1` / `radToUsMA2`).
- **Idle Current:** ~10 mA/servo (`36 × 10 mA = 0.36 A` total).
- **No-Load Running Current:** ~170 mA/servo (`36 × 170 mA = 6.12 A`).
- **Typical Loaded Walking Current:** ~400–650 mA/active servo (`~14–24 A` typical walking across stance legs).
- **Worst-Case Simultaneous Stall (@ 6.0 V):** ~2.5 A/servo (`90 A` theoretical all-36 simultaneous lock; protected against sustained stall by **dual 20 A Left/Right branch fuses** and a **40 A main fuse**).
- **Dual-Motor Stall Torque per Joint (@ 6.0 V):** `2 × 11.0 kg·cm = 22.0 kg·cm` (**`2.157 N·m`**; analytical `70%` continuous design target = **`1.510 N·m`**, pending bench thermal validation).

> **CRITICAL:** Never route 36-servo actuator current through an Arduino Mega regulator, ESP32 5V/3.3V pin, solderless breadboard, or a single PCA9685 V+ screw terminal without heavy-gauge external bus bars.

## 2. Three Supported Power Configurations

1. **Bench Testing (Stages 1–4):** Current-limited lab PSU set to **6.0 V**, 2 A limit (single servo) or 6 A limit (single 6-servo leg).
2. **Full Robot Lab Operation (Stages 5–9):** Dedicated **6.0 V, 30–40 A** regulated bench supply (or dual 20 A supplies) feeding Left (`J0..J8`, 18 servos) and Right (`J9..J17`, 18 servos) power buses via a **40 A main fuse**, **dual 20 A branch fuses**, **4700 µF low-ESR bulk capacitors**, and **hardware NC Emergency-Stop**. Separate **5.0 V / 5.0 A** buck converter for Raspberry Pi 4/5.
3. **Battery-Powered Agricultural Operation (Stages 10–11):** **3S 5000 mAh 30C–50C LiPo** pack (`11.1 V` nominal, `12.6 V` max, `~0.360 kg`, `150–250 A` burst capable) -> **40 A main fuse + E-Stop** -> high-current **6.0 V / 35 A** (or dual 20 A) DC-DC buck for servos + isolated **5.0 V / 5 A** DC-DC buck for Raspberry Pi / RP-Lidar. **10 AWG** main leads, **14 AWG** branch feeds, **XT60** connectors.

## 3. Emergency-Stop & Collapse Precaution
The hardware E-stop disconnects the **6.0 V servo power bus** independently of software while keeping logic/telemetry powered. Because MG996R gearboxes are not self-locking under full chassis load (**`3.79–4.02 kg`** G-code PLA+ + 36 servos + 3S LiPo + electronics), removing servo power causes the robot to settle onto the ground—always use a support stand during bench/lab testing.
