# HexaLoam Servo Power Supply & Electrical Engineering

## 1. MG996R Electrical & Mechanical Reference Limits (18 Joints × 2 Back-to-Back Motors = 36 Servos)
- **Nominal Operating Voltage:** 4.8 V – 7.2 V (design target: **6.0 V regulated**).
- **Actuator Pairing (`MA1` & `MA2`):** Each of the 18 logical joints uses two opposing back-to-back MG996R servos (`MA1` and `MA2`), centered at `1500 us` (90°) before mechanical coupling and driven with mirrored offsets (`MA1 = 1500 + Δus`, `MA2 = 3000 - MA1`).
  - **18-Channel Mode (the only documented wiring, Config A/B/C/D):** Each logical joint output drives `MA1` directly and `MA2` through an inline **hardware PWM servo signal reverser** (one per joint, 18 in total) fed from the same `MA1` channel (`MA2 = 3000 - MA1 us`). The default firmware therefore outputs 18 channels; `us_ma2` in `firmware/esp32/actuator-slave/src/main.cpp` and `radToUsMA2()` in the Arduino examples compute the same mirrored value the reverser produces. Without reversers, build the ESP32 environment `esp32_single_18dof_ma2_software` (`-DHEXALOAM_MA2_SOFTWARE=1`): it drives every MA2 from software on two companion PCA9685 boards (0x42 for board A, 0x43 for board B) at the same channel numbers, mirrored around 1500 us.
  - **Software-mirrored 36-channel mode: not available on the documented boards.** Two PCA9685 boards give 32 channels, fewer than the 36 needed. A software-mirrored mode would need a third PCA9685 (`0x42`, 48 channels) or extra Mega pins (`D22..D57`) plus firmware changes; it is not implemented.
- **Idle Current:** ~10 mA/servo (`36 × 10 mA = 0.36 A` total).
- **No-Load Running Current:** ~170 mA/servo (`36 × 170 mA = 6.12 A`).
- **Typical Loaded Walking Current:** ~400–650 mA/active servo (`~14–24 A` typical walking across stance legs). `hexaloam_config.json` uses the conservative **650 mA** figure (`typical_loaded_current_ma`).
- **Worst-Case Simultaneous Stall (@ 6.0 V):** ~2.5 A/servo (`90 A` theoretical all-36 simultaneous lock; protected against sustained stall by **dual 20 A Left/Right branch fuses** and a **40 A main fuse**).
- **Dual-Motor Stall Torque per Joint (@ 6.0 V):** `2 × 11.0 kg·cm = 22.0 kg·cm` (**`2.157 N·m`**; analytical `70%` continuous design target = **`1.510 N·m`**, pending bench thermal validation).

- **Mass basis:** the CAD servo model weighs `33.9 g` (`mass_per_servo_cad_kg`), while the MG996R datasheet weight is `55 g`. Every mass total in the README, site and torque analysis uses the `55 g` datasheet weight (`36 × 55 g = 1.980 kg`). The config field `total_printed_and_servo_cad_mass_kg` (`5.177 kg`) is the CAD-model total with all 36 servos at `33.9 g`.

> **CRITICAL:** Never route 36-servo actuator current through an Arduino Mega regulator, ESP32 5V/3.3V pin, solderless breadboard, or a single PCA9685 V+ screw terminal without heavy-gauge external bus bars.

## 2. Three Supported Power Configurations

1. **Bench Testing (Stages 1–4):** Current-limited lab PSU set to **6.0 V**, 2 A limit (single servo) or 6 A limit (single leg, J0..J2 = 6 servos). The **half-robot test** (Stage 5, J0..J8 = 18 servos) uses one 6.0 V / 20 A supply through one **20 A branch fuse**, i.e. the same protection as one of the two branches of the full robot.
2. **Full Robot Lab Operation (Stages 5–9):** Dedicated **6.0 V, 30–40 A** regulated bench supply (or dual 20 A supplies) feeding Left (`J0..J8`, 18 servos) and Right (`J9..J17`, 18 servos) power buses via a **40 A main fuse**, **dual 20 A branch fuses**, **4700 µF low-ESR bulk capacitors**, and **hardware NC Emergency-Stop**. Separate **5.0 V / 5.0 A** buck converter for Raspberry Pi 4/5.
3. **Battery-Powered Agricultural Operation (Stages 10–11):** **3S 5000 mAh 30C–50C LiPo** pack (`11.1 V` nominal, `12.6 V` max, `~0.360 kg`, `150–250 A` burst capable) -> **40 A main fuse + E-Stop** -> high-current **6.0 V / 35 A** (or dual 20 A) DC-DC buck for servos + isolated **5.0 V / 5 A** DC-DC buck for Raspberry Pi / RP-Lidar. **10 AWG** main leads, **14 AWG** branch feeds, **XT60** connectors.

**Battery voltage sense (diagram 14):** 3S LiPo (12.6 V full) through `R1 = 33 kΩ / R2 = 10 kΩ` gives `12.6 × 10/43 = 2.93 V` at a 3.3 V ADC pin (ESP32 GPIO34) or the Mega A0 (5 V reference). Scale factor `Vbat = ADC voltage × 4.3`; add a 100 nF filter capacitor.

## 3. Emergency-Stop & Collapse Precaution
The hardware E-stop disconnects the **6.0 V servo power bus** independently of software while keeping logic/telemetry powered. Because MG996R gearboxes are not self-locking under full chassis load (**`3.79–4.02 kg`** G-code PLA+ + 36 servos + 3S LiPo + electronics), removing servo power causes the robot to settle onto the ground—always use a support stand during bench/lab testing.
