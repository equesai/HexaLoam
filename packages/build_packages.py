"""Build 6 downloadable configuration edition manifests & READMEs under packages/."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "packages"

EDITIONS = [
    ("01_arduino_mega_beginner", "HexaLoam Arduino Mega 2560 Beginner Edition",
     ["firmware/arduino/examples/", "firmware/shared/hexaloam_joint_map.h", "electronics/wiring/01_arduino_mega_18_servos.pdf", "electronics/connection-tables/01_arduino_mega_18_servos.md", "control/calibration/"]),
    ("02_esp32_standalone", "HexaLoam ESP32 Standalone Edition",
     ["firmware/esp32/actuator-slave/", "firmware/shared/hexaloam_joint_map.h", "electronics/wiring/02_esp32_dual_pca9685.pdf", "electronics/connection-tables/02_esp32_dual_pca9685.md", "control/calibration/"]),
    ("03_rpi_single_esp32", "HexaLoam Raspberry Pi Single-ESP32 Edition",
     ["software/raspberry-pi/", "firmware/esp32/actuator-slave/", "control/robot-configuration/hexaloam_config.json", "control/communication-protocol/", "electronics/wiring/03_rpi_single_esp32_dual_pca9685.pdf"]),
    ("04_rpi_dual_esp32", "HexaLoam Raspberry Pi Dual-ESP32 Edition",
     ["software/raspberry-pi/", "firmware/esp32/actuator-slave/", "control/robot-configuration/hexaloam_config.json", "control/communication-protocol/", "electronics/wiring/04_rpi_dual_esp32_single_pca9685_each.pdf", "electronics/wiring/15_dual_controller_sync_wiring.pdf"]),
    ("05_matlab_sim_and_control", "HexaLoam MATLAB Simulation & Hardware Control Edition",
     ["simulation/matlab/", "simulation/cad-export/", "demonstrations/", "control/robot-configuration/hexaloam_config.json", "control/robot-configuration/torque_mass_analysis.json"]),
    ("06_complete_developer", "HexaLoam Complete Developer Edition",
     ["control/", "electronics/", "firmware/", "software/", "simulation/", "demonstrations/", "testing/", "Printables/", "Full_Robot_Assembly.SLDASM"]),
]


def main() -> None:
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    for slug, title, includes in EDITIONS:
        d = PKG_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.json").write_text(json.dumps({"edition": slug, "title": title, "includes": includes, "license_notice": "Released under the MIT License (see LICENSE). See CONTRIBUTING.md for how to contribute."}, indent=2) + "\n", encoding="utf-8")
        lines = [f"# {title}", "", "## Included Files & Folders", ""] + [f"- `{p}`" for p in includes] + ["", "## Quickstart", "1. Verify wiring against `electronics/wiring/` and `electronics/power/POWER_ENGINEERING.md`.", "2. Calibrate servos at 1500 us neutral before assembling horns (`control/calibration/README.md`).", "3. Follow `testing/electrical/` through `testing/locomotion/` progressively."]
        (d / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {len(EDITIONS)} downloadable edition packages.")


if __name__ == "__main__":
    main()
