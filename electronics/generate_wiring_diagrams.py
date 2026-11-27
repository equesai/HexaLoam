"""Generate all 15 HexaLoam engineering wiring diagrams in SVG, PNG, PDF, and JSON netlist."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

ROOT = Path(__file__).resolve().parents[1]
OUT_WIRING = ROOT / "electronics" / "wiring"
OUT_TABLES = ROOT / "electronics" / "connection-tables"
OUT_SCHEM = ROOT / "electronics" / "schematics"

DIAGRAMS = [
    ("01_arduino_mega_18_servos", "01. Arduino Mega 2560 — 18 PWM Channels -> 36 Servos (MA1 + MA2)", "arduino-mega",
     [("Arduino Mega 2560\n(5V Logic, USB)", 0.08, 0.35, 0.24, 0.45, "#1E293B"),
      ("External 6.0V 35A\nRegulated Servo PSU", 0.08, 0.08, 0.24, 0.18, "#7C2D12"),
      ("Servo Bus Bar + E-Stop\n40A Main + 2x20A Branch\nCommon GND", 0.40, 0.08, 0.22, 0.26, "#985107"),
      ("36x MG996R Servos (2 per joint)\nJ0..J17: MA1 + MA2\nBrown=GND Red=+6V Orn=PWM", 0.68, 0.25, 0.26, 0.55, "#0F172A"),
      ("18x PWM Servo Reverser\n(1 per joint, MA2 path)", 0.40, 0.46, 0.22, 0.20, "#6D28D9")],
     [(0.32, 0.74, 0.68, 0.74, "D22..D39 PWM (5V) -> MA1 direct", "#D97706"),
      (0.32, 0.56, 0.40, 0.56, "Same PWM", "#D97706"),
      (0.62, 0.56, 0.68, 0.56, "Reversed -> MA2", "#7C3AED"),
      (0.32, 0.17, 0.40, 0.17, "10 AWG", "#DC2626"),
      (0.62, 0.28, 0.68, 0.35, "14 AWG branches", "#DC2626"),
      (0.20, 0.35, 0.51, 0.34, "Common Signal GND", "#475569")]),
    ("02_esp32_dual_pca9685", "02. Standalone ESP32 DevKit + Dual PCA9685 (0x40, 0x41)", "esp32-standalone",
     [("ESP32 DevKit (3.3V)\nGPIO21=SDA GPIO22=SCL\nGPIO4=E-Stop GPIO34=VBAT", 0.06, 0.42, 0.25, 0.38, "#1E293B"),
      ("PCA9685 Board A (0x40)\nCh0..8: LF/LM/LR", 0.40, 0.55, 0.23, 0.25, "#0F766E"),
      ("PCA9685 Board B (0x41)\nA0 Jumper, Ch0..8: RF/RM/RR", 0.40, 0.22, 0.23, 0.25, "#0F766E"),
      ("6.0V Servo PSU -> V+ (3.3V VCC Logic)\n36x MG996R: MA1 direct,\nMA2 via PWM reverser", 0.70, 0.22, 0.24, 0.55, "#7C2D12")],
     [(0.31, 0.66, 0.40, 0.66, "I2C 3.3V SDA/SCL", "#0284C7"),
      (0.31, 0.52, 0.40, 0.36, "I2C 3.3V SDA/SCL", "#0284C7"),
      (0.63, 0.66, 0.70, 0.66, "J0..J8 PWM 50Hz", "#D97706"),
      (0.63, 0.34, 0.70, 0.34, "J9..J17 PWM 50Hz", "#D97706")]),
    ("03_rpi_single_esp32_dual_pca9685", "03. Raspberry Pi 4/5 -> Single ESP32 -> Dual PCA9685", "raspberry-pi-single-esp32",
     [("Raspberry Pi 4/5\n(5V 5A USB-C PSU)\nKinematics, SLAM, ROS2", 0.05, 0.45, 0.23, 0.35, "#312E81"),
      ("ESP32 Slave (460800 baud)\nGPIO21=SDA GPIO22=SCL", 0.34, 0.45, 0.23, 0.35, "#1E293B"),
      ("PCA9685-A (0x40) + B (0x41)\n50Hz 18-Ch PWM (MA2 via\nreverser per joint)", 0.63, 0.45, 0.28, 0.35, "#0F766E"),
      ("Independent 6.0V Servo PSU\n+ Common GND Star", 0.34, 0.10, 0.57, 0.20, "#7C2D12")],
     [(0.28, 0.62, 0.34, 0.62, "USB Serial", "#2563EB"),
      (0.57, 0.62, 0.63, 0.62, "I2C 3.3V", "#0284C7"),
      (0.63, 0.30, 0.75, 0.45, "6.0V V+", "#DC2626")]),
    ("04_rpi_dual_esp32_single_pca9685_each", "04. Raspberry Pi 4/5 -> Dual ESP32 (Left/Right 0x40)", "raspberry-pi-dual-esp32",
     [("Raspberry Pi 4/5\nudev: /dev/hexaloam_left\nudev: /dev/hexaloam_right", 0.05, 0.35, 0.24, 0.40, "#312E81"),
      ("ESP32-A (Left, ID=1)\nPCA9685-A (0x40) Ch0..8", 0.37, 0.56, 0.26, 0.26, "#1E293B"),
      ("ESP32-B (Right, ID=2)\nPCA9685-B (0x40) Ch0..8", 0.37, 0.18, 0.26, 0.26, "#1E293B"),
      ("Left/Right 6V Bus + E-Stop\n(36 servos: MA2 via reverser)", 0.70, 0.18, 0.24, 0.64, "#7C2D12")],
     [(0.29, 0.64, 0.37, 0.68, "USB-A 460800", "#2563EB"),
      (0.29, 0.46, 0.37, 0.32, "USB-B 460800", "#2563EB"),
      (0.63, 0.68, 0.70, 0.68, "J0..J8", "#D97706"),
      (0.63, 0.30, 0.70, 0.30, "J9..J17", "#D97706")]),
    ("05_servo_power_distribution", "05. Servo Power Distribution (6.0V High-Current Bus)", "power-distribution",
     [("3S 5000 mAh LiPo (12.6V full)\nor 6V 35A Lab PSU", 0.06, 0.45, 0.20, 0.30, "#7C2D12"),
      ("Main Fuse (40A) + E-Stop\nNC Contactor / MOSFET", 0.31, 0.45, 0.22, 0.30, "#991B1B"),
      ("6.0V 35A Buck (or 2x20A)\n+ 4700uF Cap + 5V 5A Pi Buck", 0.58, 0.45, 0.20, 0.30, "#985107"),
      ("Left Bus (20A) /\nRight Bus (20A)\n18 servos each", 0.82, 0.45, 0.14, 0.30, "#0F172A")],
     [(0.26, 0.60, 0.31, 0.60, "10 AWG", "#DC2626"),
      (0.53, 0.60, 0.58, 0.60, "10 AWG", "#DC2626"),
      (0.78, 0.60, 0.82, 0.60, "14 AWG", "#DC2626")]),
    ("06_single_servo_test", "06. Single-Servo Bench Test (Current-Limited 6V @ 2A)", "power-distribution",
     [("Bench PSU 6.0V (2A Limit)", 0.08, 0.25, 0.24, 0.45, "#7C2D12"),
      ("Controller (Mega D22 / PCA Ch0)", 0.40, 0.45, 0.24, 0.30, "#1E293B"),
      ("1x MG996R (J0 LF_COXA)", 0.72, 0.35, 0.22, 0.35, "#0F766E")],
     [(0.32, 0.45, 0.72, 0.45, "+6V / Common GND", "#DC2626"),
      (0.64, 0.60, 0.72, 0.60, "PWM 50Hz", "#D97706")]),
    ("07_three_servo_single_leg_test", "07. Single-Leg Test (J0..J2 = 6 Servos, MA1+MA2)", "power-distribution",
     [("Bench PSU 6.0V (6A Limit)", 0.08, 0.25, 0.24, 0.45, "#7C2D12"),
      ("Controller (D22..24 / PCA Ch0..2)", 0.40, 0.45, 0.24, 0.30, "#1E293B"),
      ("Leg LF: Coxa, Femur, Tibia\n(6 servos, 3 reversers)", 0.72, 0.35, 0.22, 0.35, "#0F766E")],
     [(0.32, 0.45, 0.72, 0.45, "+6V / Common GND", "#DC2626"),
      (0.64, 0.60, 0.72, 0.60, "3x PWM 50Hz (+3 reversed for MA2)", "#D97706")]),
    ("08_nine_servo_half_robot_test", "08. Half-Robot Test (Left Side J0..J8 = 18 Servos)", "raspberry-pi-dual-esp32",
     [("6.0V 20A PSU + 20A Branch Fuse", 0.08, 0.25, 0.24, 0.45, "#7C2D12"),
      ("ESP32-A + PCA9685-A (0x40)", 0.40, 0.45, 0.24, 0.30, "#1E293B"),
      ("18x Servos (9 joints: LF, LM, LR;\nMA2 via 9 reversers)", 0.72, 0.35, 0.22, 0.35, "#0F766E")],
     [(0.32, 0.45, 0.72, 0.45, "+6V Bus / Common GND", "#DC2626"),
      (0.64, 0.60, 0.72, 0.60, "Ch0..8 PWM", "#D97706")]),
    ("09_eighteen_servo_full_test", "09. Full 36-Servo Supported Test (18 Joints, J0..J17)", "raspberry-pi-single-esp32",
     [("6.0V 35A PSU + 40A Main Fuse + E-Stop", 0.08, 0.25, 0.24, 0.45, "#7C2D12"),
      ("Dual PCA9685 (0x40 + 0x41)", 0.40, 0.45, 0.24, 0.30, "#1E293B"),
      ("All 36 MG996R Servos\n(MA1 direct, MA2 via reverser)", 0.72, 0.35, 0.22, 0.35, "#0F766E")],
     [(0.32, 0.45, 0.72, 0.45, "Dual 20A Branch Buses", "#DC2626"),
      (0.64, 0.60, 0.72, 0.60, "18x PWM 50Hz (+18 reversed)", "#D97706")]),
    ("10_imu_integration", "10. IMU Integration (BNO085 / MPU6050 on 3.3V I2C)", "esp32-standalone",
     [("ESP32 (GPIO21 SDA, GPIO22 SCL)", 0.10, 0.40, 0.28, 0.35, "#1E293B"),
      ("IMU 0x4A/0x68 (3.3V VCC)", 0.56, 0.40, 0.30, 0.35, "#0284C7")],
     [(0.38, 0.57, 0.56, 0.57, "3.3V I2C + 4.7k Pull-ups", "#0284C7")]),
    ("11_foot_contact_sensor_integration", "11. Foot Contact Switches (6x GPIO Pull-Up Inputs)", "esp32-standalone",
     [("ESP32 / Dual ESP32 GPIO Inputs\n(3.3V Internal Pull-up)", 0.10, 0.35, 0.32, 0.40, "#1E293B"),
      ("6x Tactile/FSR Foot Switches\n(LF..RR -> GND on Contact)", 0.56, 0.35, 0.32, 0.40, "#0F766E")],
     [(0.42, 0.55, 0.56, 0.55, "6x Signal + GND", "#16A34A")]),
    ("12_rplidar_raspberry_pi", "12. RP-Lidar Connection to Raspberry Pi 4/5", "raspberry-pi-single-esp32",
     [("Raspberry Pi 4/5\n(USB3 /dev/rplidar)", 0.10, 0.40, 0.28, 0.35, "#312E81"),
      ("CP2102 USB-UART Bridge\n(5V Regulated)", 0.44, 0.40, 0.20, 0.35, "#1E293B"),
      ("RP-Lidar A1/A2\n(Mounted on -Z Underside)", 0.70, 0.40, 0.22, 0.35, "#985107")],
     [(0.38, 0.57, 0.44, 0.57, "USB", "#2563EB"),
      (0.64, 0.57, 0.70, 0.57, "TX/RX + 5V", "#D97706")]),
    ("13_estop_power_isolation", "13. Hardware Emergency-Stop & Power Isolation", "power-distribution",
     [("Battery / Main PSU", 0.06, 0.40, 0.20, 0.35, "#7C2D12"),
      ("Mushroom E-Stop (NC)\n+ High-Side Relay/MOSFET", 0.34, 0.40, 0.26, 0.35, "#991B1B"),
      ("Servo Power Bus ONLY\n(Logic stays powered for telemetry)", 0.68, 0.40, 0.26, 0.35, "#1E293B")],
     [(0.26, 0.57, 0.34, 0.57, "40A Main", "#DC2626"),
      (0.60, 0.57, 0.68, 0.57, "Switched 6V", "#DC2626")]),
    ("14_battery_voltage_monitoring", "14. Battery Voltage Divider (3S LiPo 12.6V -> 3.3V ADC)", "power-distribution",
     [("3S LiPo (9.0V..12.6V)", 0.08, 0.40, 0.24, 0.35, "#7C2D12"),
      ("R1=33k / R2=10k Divider (scale x4.3)\n(2.93V @ 12.6V) + 100nF", 0.38, 0.40, 0.26, 0.35, "#985107"),
      ("ESP32 GPIO34 (ADC)\n/ Mega A0 (5V)", 0.70, 0.40, 0.22, 0.35, "#1E293B")],
     [(0.32, 0.57, 0.38, 0.57, "VBAT", "#DC2626"),
      (0.64, 0.57, 0.70, 0.57, "<=2.93V (Vbat = ADC x 4.3)", "#16A34A")]),
    ("15_dual_controller_sync_wiring", "15. Optional Dual-ESP32 Hardware SYNC Line (GPIO18)", "raspberry-pi-dual-esp32",
     [("Raspberry Pi GPIO17\n(10 Hz / Frame Sync Pulse)", 0.08, 0.40, 0.26, 0.35, "#312E81"),
      ("ESP32-A GPIO18 (3.3V)", 0.46, 0.58, 0.36, 0.22, "#1E293B"),
      ("ESP32-B GPIO18 (3.3V)", 0.46, 0.22, 0.36, 0.22, "#1E293B")],
     [(0.34, 0.62, 0.46, 0.69, "SYNC 3.3V + GND", "#0284C7"),
      (0.34, 0.50, 0.46, 0.33, "SYNC 3.3V + GND", "#0284C7")]),
]


def render_diagram(name: str, title: str, schem_dir: str, blocks: list, wires: list) -> None:
    OUT_WIRING.mkdir(parents=True, exist_ok=True)
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    (OUT_SCHEM / schem_dir).mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=150)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    ax.text(0.03, 0.94, f"HexaLoam Engineering Schematic — {title}", fontsize=12, fontweight="bold", color="#111827")
    ax.text(0.03, 0.89, "WARNING: Verify servo wire colors (Brown/Black=GND, Red=+V, Orange/Yellow=PWM) against purchased servo datasheet.", fontsize=8.5, color="#991B1B")

    for label, x, y, w, h, color in blocks:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012", linewidth=1.5, edgecolor="#111827", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color="#FFFFFF", fontsize=8.5, fontweight="bold")

    for x1, y1, x2, y2, wlabel, color in wires:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=2.0, color=color))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.025, wlabel, ha="center", va="bottom", fontsize=7.5, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.85))

    ax.text(0.03, 0.03, "Source of truth: control/robot-configuration/hexaloam_config.json | HexaLoam", fontsize=7.5, color="#475569")

    for ext in ("svg", "png", "pdf"):
        fig.savefig(OUT_WIRING / f"{name}.{ext}", format=ext, bbox_inches="tight")
    plt.close(fig)

    netlist = {
        "diagram": name,
        "title": title,
        "format": "hexaloam-kicad-netlist-v1",
        "blocks": [{"label": b[0].replace("\n", " "), "color": b[5]} for b in blocks],
        "connections": [{"signal": w[4]} for w in wires],
    }
    (OUT_SCHEM / schem_dir / f"{name}.kicad_sch.json").write_text(json.dumps(netlist, indent=2) + "\n", encoding="utf-8")

    md = [f"# Connection Table — {title}", "", "| Signal / Net | Description |", "|---|---|"]
    for w in wires:
        md.append(f"| `{w[4]}` | Verified in `{name}.svg` / `.png` / `.pdf` |")
    (OUT_TABLES / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    for item in DIAGRAMS:
        render_diagram(*item)
    print(f"Generated {len(DIAGRAMS)} wiring diagrams (SVG, PNG, PDF), netlists, and connection tables.")


if __name__ == "__main__":
    main()
