# HexaLoam for agricultural plant inspection (camera vision guide)

This guide is for a graduation project, thesis or research prototype that needs an **open-source hexapod (hexabot) for crop or greenhouse scouting**, with a camera that finds plant defects, an editable SOLIDWORKS design, MATLAB simulation files, and a low-cost, fully 3D-printed body. It says what HexaLoam already provides, what you must add, and how to add it. Nothing here claims more than the repository contains.

> **Honest status.** HexaLoam has **no camera mount in the CAD yet and no plant-vision code**. Everything in sections 3 to 5 is a design path for you to build, not a feature that ships. Physical bench tests of the robot are still pending (see [section 8](#8-limitations)).

## 1. Why HexaLoam fits this use case

| Your requirement | What the repository provides |
| --- | --- |
| Editable SOLIDWORKS design | Native parts and assemblies: [Full_Robot_Assembly.SLDASM](../Full_Robot_Assembly.SLDASM), [LegMates.SLDASM](../LegMates.SLDASM), [Designed/](../Designed/) |
| Fully 3D-printable body | 5 STL designs = 20 printed pieces (chassis, 6x L1, 6x L2, 6x L3, LiDAR cover), PLA+ printed mass 1.306 kg (Bambu Studio, supports excluded). [STL, 3MF](../Printables/), GLB and STEP also included |
| Cheap servos | 18 joints (3 per leg) driven by 36 MG996R servos, two back-to-back per joint |
| LiDAR | RP-Lidar (2D) mount and cover are already in the chassis CAD |
| MATLAB simulation | Simscape Multibody XML export + STEP, single-leg static study, gait trajectory replay, URDF for `importrobot` ([simulation guide](simulation-guide.md)) |
| Electronics and software | Four controller configurations (A-D), 15 wiring diagrams, Arduino and ESP32 firmware, Raspberry Pi Python and ROS 2 controller, 3S 5000 mAh LiPo |
| Torque check | Mass and required torque per configuration and gait ([README table](../README.md#electronics-firmware-wiring--torque-analysis)) |
| License | [MIT](../LICENSE): modify, print and publish your derivative |

The robot was **tested in four controller configurations (A-D) by simulation parameters and analysis**: the mass of each configuration's controllers and top-mounted parts was compared with the torque each set of motors needs. This is analytical testing, not a physical bench test. Wave and ripple gaits stay within 70 % of continuous torque in all four; tripod needs 81-86 %.

## 2. Pick a configuration

A camera plus on-board inference needs a computer, so use **Configuration C (Raspberry Pi 4/5 + 1 ESP32 + RP-Lidar)** or **D (Raspberry Pi + 2 ESP32)**. They also run the ROS 2 controller. Configurations A and B (Arduino Mega, ESP32) have no computer for vision, though they can still walk.

Budget the camera mass: a Raspberry Pi Camera Module 3 with its bracket is a few tens of grams, well inside the payload headroom listed for configurations C and D in wave and ripple gaits (README table). Re-run the torque estimate if you add a heavier payload such as a battery for a second computer or a Jetson.

## 3. Add a camera

1. **Camera choice.** Raspberry Pi Camera Module 3 (CSI, autofocus, about 66-75 degree field of view depending on variant) is the simplest with a Raspberry Pi. A USB camera is easier to swap and to test on a laptop first.
2. **Placement.** Mount it at the front edge of the chassis deck, looking forward and down. Use the existing **M3 holes and nut pockets** of [Robot_Base.SLDPRT](../Designed/Robot_Base.SLDPRT) for a printed bracket; measure them in the CAD, do not guess.
3. **Field of view versus legs.** In SOLIDWORKS, sweep the front legs through their full gait range (see [LegMates.SLDASM](../LegMates.SLDASM)) and check that no foot, coxa or tibia crosses the camera cone. Raise the camera on a short mast if the front legs enter the frame.
4. **Tilt.** Plants are on the ground ahead, so tilt 20-40 degrees down and use an adjustable bracket (slotted M3 holes) so you can tune it on the bench. For leaf-underside checks you need a different, lower or sideways mount.
5. **Vibration and cable.** Use a rigid bracket, strain-relieve the ribbon cable, and keep the LiDAR scan plane clear of the camera mount. Prefer slow wave or ripple gaits for sharper frames.
6. **Print and publish.** Add the bracket to the CAD as a new part, print one, and contribute it back (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## 4. Perception pipeline (to build)

1. **Data collection.** Drive or walk the robot along real rows, or photograph plants by hand. Record images with the robot's pose (section 4.4). Use many plants, lighting conditions and growth stages; keep a held-out test set from different plants.
2. **Label.** Annotate leaf defects in a tool such as CVAT or Label Studio. Decide the classes first (for example healthy, spots, blight, pest damage).
3. **Train a detector or segmenter.** YOLO-family detection is quick to train and runs on a Raspberry Pi with a small model; use instance segmentation if you need leaf area. Report precision, recall and per-class results on the held-out set, and say plainly that results from one crop or greenhouse do not transfer to another without retraining.
4. **Severity by affected area.** With a segmentation mask, severity = defect pixels / leaf pixels (a simple, explainable score you can bin into low, medium, high). A camera at a known height and tilt lets you convert pixels to approximate area, but calibrate it.
5. **Geotag with the SLAM pose.** The RP-Lidar supports **2D SLAM** (for example `slam_toolbox` in ROS 2) in a row or greenhouse. Log each detection with the map pose and a timestamp to build a defect map.
6. **ROS 2 wiring.** The existing node publishes `joint_states` and subscribes to `cmd_vel` ([hexaloam_ros2_node.py](../software/raspberry-pi/hexaloam_controller/ros2/hexaloam_ros2_node.py)). A typical design adds your own camera node publishing `/image_raw`, a detector node publishing a detection message with severity, and a logger that joins detections with the SLAM pose (`/map` and TF). These extra nodes are yours to write.

## 5. MATLAB and Simulink digital-twin path

Use this to validate gait, sensing and the inspection route before printing anything.

- **Body and legs.** Simscape Multibody from the CAD export (`simulation/cad-export/`) imports and compiles in MATLAB R2025b, but contains **29 extra 6-DOF joints** from missing CAD mates. Until the mates are fixed, use [`simulation/urdf/hexaloam.urdf`](../simulation/urdf/hexaloam.urdf) with `importrobot` as the clean 18-joint kinematic model. `python tools/check_cad_mates.py simulation/cad-export/Full_Robot_Assembly.xml` explains the extra joints.
- **Existing scripts.** [`legStaticStudy.m`](../simulation/matlab/legStaticStudy.m) (foot force to joint torque) and [`replay_gait_trajectory.m`](../simulation/matlab/replay_gait_trajectory.m) (gait replay).
- **Agricultural scene.** MathWorks pairs R2025b with Unreal Engine 5.3 and its Robotics System Toolbox Interface for Unreal Engine Projects. Start from a MathWorks example scene, then build one crop row, one known robot pose and one sensor target ([simulation guide](simulation-guide.md#full-robot-and-agricultural-scene)).
- **Sensors.** Use the camera and lidar sensor blocks of the Unreal co-simulation (or Simulation 3D blocks) to generate synthetic images and scans, and test the perception pipeline's interfaces. Synthetic leaves are not real disease, so train and evaluate on real photographs.
- **Assessment files.** Keep your model, the scenario script, the test cases and a short results table together so a supervisor can rerun them.

## 6. Which gait for inspection

| Gait | Feet on ground | Required torque (configs A-D) | Use for inspection |
| --- | --- | --- | --- |
| Wave | 5 | 45-48 % of stall | Slowest, steadiest, lowest vibration; best for image capture |
| Ripple | 4 | 59-62 % | Good balance of speed and smoothness; within the 70 % continuous limit |
| Tripod | 3 | 81-86 % | Fastest, but above the 70 % limit; short unloaded runs only |

The Raspberry Pi controller and quickstart default to tripod; select ripple or wave before adding a camera and computer. Stop walking for the exposure if your camera needs sharp, still frames.

## 7. Suggested project plan

1. Print one leg set, then the rest; assemble and run the staged [testing guides](../testing/).
2. Design and print the camera bracket; check clearances in CAD, then on the bench.
3. Collect and label data; train and evaluate the detector.
4. Build the ROS 2 detection and logging nodes; test indoors with potted plants.
5. Build the MATLAB digital twin and compare its predicted torque and gait with measurements.
6. Document results honestly, including failures, and cite the project ([CITATION.cff](../CITATION.cff)).

## 8. Limitations

- **No camera mount in the CAD and no plant-vision code** are included. You design and write them.
- **The Simscape import has 29 extra 6-DOF joints** until the missing CAD mates are added; use the URDF for a clean kinematic model.
- **URDF and Gazebo/Isaac dynamics are not verified** against the hardware; the URDF is a kinematic model.
- **Physical validation is pending.** Weight and torque figures are analytical estimates from slicer-reported masses, not bench measurements.
- **MG996R servos are hobby servos.** Two per joint give 2.157 N.m stall at 6 V, but continuous load, heat, backlash and gear wear matter in the field; the 70 % continuous limit is a design margin, not a guarantee. Rough, wet or muddy ground is not validated.
- **2D LiDAR only.** The RP-Lidar supports 2D SLAM; "LOAM" in the project name is not a claim of 3D LOAM odometry.

## Related

[README](../README.md) · [Designer guide](designer-guide.md) · [Simulation guide](simulation-guide.md) · [Walking gaits](walking.md) · [BOM](../electronics/bom/BOM.md) · [Wiring diagrams](../electronics/wiring/)
