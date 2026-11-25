"""Generate downloadable CSV/JSON gait trajectories and plots for Tripod, Ripple, and Wave."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software" / "raspberry-pi"))

from hexaloam_controller.kinematics.hexapod_kinematics import LEG_ORDER
from hexaloam_controller.locomotion.gait_engine import GaitEngine


def export_gait(gait_name: str) -> None:
    out_dir = ROOT / "demonstrations" / gait_name
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = GaitEngine()
    engine.set_gait(gait_name)
    joint_names = [j["name"] for j in engine.kin.config["joints"]]

    dt = 0.05
    steps = int(round(engine.gaits[gait_name].cycle_s / dt))
    rows = []
    json_frames = []
    q_hist = []
    stance_hist = []

    for idx in range(steps):
        t = round(idx * dt, 4)
        q, feet, stance = engine.step(dt=dt, vx=0.03)
        q_hist.append(q.copy())
        stance_hist.append([1 if stance[l] else 0 for l in LEG_ORDER])
        row = [t] + [round(float(v), 5) for v in q] + [1 if stance[l] else 0 for l in LEG_ORDER]
        rows.append(row)
        json_frames.append({
            "time_s": t,
            "gait": gait_name,
            "joints_rad": [round(float(v), 5) for v in q],
            "stance": stance,
            "feet_m": {l: [round(float(c), 5) for c in feet[l]] for l in LEG_ORDER},
        })

    csv_path = out_dir / f"{gait_name}_trajectory.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time_s"] + joint_names + [f"{l}_stance" for l in LEG_ORDER])
        w.writerows(rows)

    (out_dir / f"{gait_name}_trajectory.json").write_text(
        json.dumps({"gait": gait_name, "dt_s": dt, "frames": json_frames}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Plot joint trajectories + stance phase diagram
    q_arr = np.array(q_hist)
    st_arr = np.array(stance_hist)
    times = np.arange(steps) * dt
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5.5), dpi=130, sharex=True)
    ax1.plot(times, q_arr[:, 0], label="LF_COXA")
    ax1.plot(times, q_arr[:, 1], label="LF_FEMUR")
    ax1.plot(times, q_arr[:, 2], label="LF_TIBIA")
    ax1.set_ylabel("Angle (rad)")
    ax1.set_title(f"HexaLoam {gait_name.title()} Gait — Software-Generated Trajectory (Software Validated)")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2.imshow(st_arr.T, aspect="auto", cmap="YlOrBr", extent=[0, times[-1], 5.5, -0.5])
    ax2.set_yticks(range(6))
    ax2.set_yticklabels(LEG_ORDER)
    ax2.set_xlabel("Time (s) — Dark = Stance, Light = Swing")
    fig.tight_layout()
    fig.savefig(out_dir / f"{gait_name}_analysis.png", dpi=130)
    plt.close(fig)

    (out_dir / "README.md").write_text(
        f"# HexaLoam {gait_name.title()} Gait Demonstration\n\n"
        f"- **Downloadable Trajectories:** [`{gait_name}_trajectory.csv`]({gait_name}_trajectory.csv) · [`{gait_name}_trajectory.json`]({gait_name}_trajectory.json)\n"
        f"- **Trajectory & Stance Plot:** [`{gait_name}_analysis.png`]({gait_name}_analysis.png)\n"
        f"- **Validation Status:** Software validated (`pytest` + `GaitEngine`); physical hardware gait validation pending bench/full-robot Stages 8–11.\n",
        encoding="utf-8",
    )


def main() -> None:
    for g in ("tripod", "ripple", "wave"):
        export_gait(g)
    print("Generated tripod, ripple, and wave trajectory datasets and plots.")


if __name__ == "__main__":
    main()
