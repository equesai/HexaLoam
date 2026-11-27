"""Generate the 11 progressive hardware testing stage guides & results templates."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "testing"

STAGES = [
    ("electrical", "Stage 01 — Electrical Verification", "Verify 6.0V servo PSU, 5V/3.3V logic rails, common GND, I2C pull-ups, 40A main and 20A branch fuses, and NC E-stop before connecting servos."),
    ("single-servo", "Stage 02 — Single Servo Bench Test", "Connect 1x MG996R (J0 LF_COXA) to 6.0V @ 2A current-limited PSU; verify 1500 us neutral, direction, and E-stop."),
    ("single-leg", "Stage 03 — Single Leg (3 Joints, 6 Servos) Test", "Verify LF leg (J0..J2) on a support fixture; validate FK/IK, travel limits, and collision clearance."),
    ("single-leg/six-legs", "Stage 04 — Six Individual Legs Check", "Test each of the 6 legs independently; verify mirrored left/right directions (+1/-1) and consistent foot coordinates."),
    ("half-robot", "Stage 05 — Half-Robot Test (9 Joints, 18 Servos)", "Validate 1x ESP32 + PCA9685 controlling 9 joints = 18 servos (J0..J8), watchdog timeout, and 6.0V bus stability."),
    ("full-robot", "Stage 06 — Full Robot Supported Test (18 Joints, 36 Servos)", "With chassis elevated on a stand, verify all 18 joints (36 servos), neutral pose, current draw, and E-stop."),
    ("full-robot/static-standing", "Stage 07 — Static Standing Load Test", "Gradually transfer chassis weight (~5.66–5.88 kg) onto 6 legs; monitor femur servo temperature and bus voltage."),
    ("locomotion", "Stage 08 — Individual Gait Testing (Wave -> Ripple -> Tripod)", "Start with slow Wave gait (5 legs stance), progress to Ripple (4 legs), then Tripod (3 legs)."),
    ("communication", "Stage 09 — Dual ESP32 Synchronization Test", "Validate udev symlinks, sequence numbers, execution timestamps, packet loss, and coordinated E-stop."),
    ("communication/rpi-autonomous", "Stage 10 — Raspberry Pi Autonomous & LiDAR Test", "Validate RP-Lidar scan, ROS2 joint_states/cmd_vel, obstacle avoidance, and telemetry logging."),
    ("agricultural", "Stage 11 — Agricultural Terrain Evaluation", "Evaluate flat soil, loose loam, gravel, grass, slopes, and payload effects after lab sign-off."),
]


def main() -> None:
    for rel, title, summary in STAGES:
        d = TEST_DIR / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "README.md").write_text(
            f"# {title}\n\n"
            f"**Objective:** {summary}\n\n"
            f"## Validation Status\n"
            f"- Current Status: `Not tested` (hardware required; no hardware test has been run).\n"
            f"- Allowed status labels: `Not tested`, `Software validated`, `Simulation validated`, `Bench hardware validated`, `Full robot validated`, `Field validated`, `Failed`.\n\n"
            f"## Results Template\n\n"
            f"| Check | Expected | Measured | Status |\n"
            f"|---|---|---|---|\n"
            f"| Supply voltage | 6.0 V ± 0.1 V | _TBD_ | `Not tested` |\n"
            f"| E-stop cutoff | Immediate servo power isolation | _TBD_ | `Not tested` |\n"
            f"| Thermal / current | Within MG996R spec | _TBD_ | `Not tested` |\n",
            encoding="utf-8",
        )
    print(f"Generated {len(STAGES)} progressive testing stage guides.")


if __name__ == "__main__":
    main()
