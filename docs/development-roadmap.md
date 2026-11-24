# HexaLoam engineering development roadmap

**Objective.** Take the HexaLoam contributors mechanical hexapod from editable CAD to a reproducible, instrumented agricultural scouting experiment. A researcher should be able to reproduce the gait, payload, terrain and sensor results from a tagged revision. A student should be able to inspect one leg and reproduce a smaller experiment before moving on to the full robot.

**First engineering priority.** Recover the complete multibody export and validate one leg. A visually correct mesh cannot establish a hinge axis, an independent degree of freedom or a motor torque requirement. Engine scene preparation and print-fit studies can proceed alongside this work.

## Starting evidence

| Area | Available evidence | Open work |
| --- | --- | --- |
| Mechanical design | Main and leg assemblies opened in SOLIDWORKS. Five custom print designs make 20 pieces. | The separate battery reference lacks its spacer part. Payload capacity, stiffness, fatigue and real-world fit require tests. |
| Visual interchange | Five part-level GLB files, their source STLs and a rebuild tool. | Record native Unity and Unreal Editor imports and integration tests. Assembly pivots and constraints require separate data. |
| Dynamics | MATLAB R2025b, Simulink, Simscape Multibody and Multibody Link were available in the development environment. | The available robot XML ends inside the parts list. Complete the export, verify geometry and inspect the imported model. |
| Sensing and field work | The CAD includes an RP-Lidar reference model and a printable cover. | Measure the sensor pose and scan clearance, add timestamped data, and validate with the chosen hardware. |
| Hardware | Chassis mounting holes and M3 nut pockets allow application-specific brackets, controllers and batteries. | Establish a configuration-specific BOM, wiring, power budget and test record. |

## Work sequence and acceptance

The sequence below is ordered by dependency. Advance a milestone when another contributor can reproduce its acceptance test. Record the repository revision, tool versions, input files, commands and observed result. Keep simulated, calculated and measured values distinguishable in each record.

### 1. Freeze a reproducible CAD and manufacturing baseline

**Deliverables.** Produce a dependency report, Pack and Go set, dimensioned assembly and exploded views, neutral STEP exchange and a provenance inventory. Identify the chassis datums, sensor frame, mounting-hole coordinates, M3 nut-pocket dimensions and tool access. Specify whether the mounting pattern is regular. Create a blank adapter drawing with measured dimensions. Record external component origin and terms separately from original parts.

**Acceptance.** Open the assembly on a clean machine with the original file locations unavailable. Rebuild the reference configuration, log warnings and verify the named references. Print a fit coupon for nuts, screws, servo flanges and candidate bearings. Record actual deviations, orientation, printer and material.

### 2. Establish one leg, then all 18 leg axes

**Deliverables.** Export the entire assembly to Simscape XML with its companion geometry and relative file references. Define a right-handed body frame and a leg naming convention for left/right and front/middle/rear. For each of three joints per leg, record the CAD mate, parent and child, axis, origin, home angle, positive direction, physical connector, CAD limits and controller limits. Inspect angular mate limits in SOLIDWORKS and enter validated limits in the model. MATLAB's CAD importer requires separate handling of joint limits. [MathWorks import reference](https://www.mathworks.com/help/sm/ref/smimport.html)

**Acceptance.** In R2025b, import into an empty working directory. Resolve all geometry, validate mass, center of mass and inertia units, and check that the model compiles. Ground the body for a bench test. Move each leg joint separately, verify the physical axis and sign against CAD, and record coupled or locked motion. Require six independent three-joint chains and 18 independently movable leg coordinates. Count any free-body motion separately. Archive the joint table, sweep traces and a one-leg animation.

### 3. Qualify the load path, actuator and printed parts

**Deliverables.** Define a measured mass budget and payload envelope. Compare standing, walking, turning and uneven-contact load cases. Calculate joint torque from force moment arms and inertial loads, then compare with the multibody result. Include backlash, servo shaft radial loads, link deflection, stress concentrations, bearing supports and access for leg replacement. Evaluate MG996R and candidate DS3218/DS3235 adapter designs against actual dimensions and sustained operating data. Parameterize leg lengths, mount positions and body dimensions in a working CAD revision.

**Acceptance.** Report assumptions and sensitivity to payload position, print direction and material. Sweep the full mechanical range for interference. Use a bench fixture to compare predicted and measured joint deflection, current, temperature and torque. Approve an actuator and payload only for the tested duty cycle. Report the limiting joint.

**Print qualification.** Slice on the proposed 256 mm bed and check skirt, brim, supports and travel margins. Test PLA+, PETG, ABS and ASA only for the profiles to be released. Publish layer height, walls, infill, orientation, fit allowance, filament use, print time and cost basis for each qualified configuration. Compare captive M3 nuts with heat-set inserts on a repeatedly serviced joint.

### 4. Develop kinematics, gaits and contact experiments

**Deliverables.** Derive forward and inverse kinematics from the verified frames. Cover alternate solutions, unreachable targets, singularities and joint limits. Begin with tripod gait, then compare ripple and wave gaits using the same foot-target interface. Define terrain height, friction and foot-contact parameters. Begin with flat ground, then introduce a ramp, step, uneven headland and crop row. Record any soil deformation study as a separately calibrated experiment.

**Acceptance.** Reconstruct reachable foot targets using forward kinematics and report Cartesian error. Confirm that unreachable targets produce a documented result. Log joint angles, speeds, peak and RMS torques, foot forces, slip, body attitude and stability margin over a complete gait. Save a baseline run, one failure case and the commands and parameters to replay both. Publish commanded and achieved motion separately.

### 5. Connect Unity and Unreal Engine

**Deliverables.** Begin with the static meshes and dimension check in the [simulation guide](simulation-guide.md). Build a Unity prefab and an Unreal actor only after mapping each part to the assembly frames. Add simplified collision bodies, joint limits and independent motion tests. For coupled experiments, assign mechanical dynamics to Simscape and feed timestamped poses to the visualization engine. Define world/body/sensor axes, handedness, unit conversions, rotation convention, simulation step and latency budget.

**Acceptance.** Record the editor, importer and package versions. Check dimensions, one known translation and a positive rotation about each axis. Replay the same trajectory in both engines and compare transforms and timestamps against the source log. Publish coverage by engine and version. A passing static import qualifies visual geometry only.

### 6. Build an agricultural environment and sensor experiment

**Deliverables.** For the R2025b co-simulation track, target Unreal Engine 5.3 with the Robotics System Toolbox Interface for Unreal Engine Projects support package. Create an original crop-row scene with a flat lane, sloped section, headland, obstacles and known sensor targets. Pair visible terrain with explicit Simscape contact surfaces. MathWorks' Rolling Vineyard is a later-release reference for scene layout. [Release compatibility](https://www.mathworks.com/help/robotics/ug/unreal-engine-simulation-environment-requirements-and-limitations.html) · [MathWorks vineyard reference and views](https://www.mathworks.com/help/robotics/ref/rollingvineyard.html)

**Sensor configurations.** Select the actual LiDAR before setting scan plane, range and angular resolution. Evaluate A1, A2 and C1 adapters individually, including vibration isolation, height adjustment, cable exit and occlusion over the gait cycle. Define transform tables for camera, IMU, optional depth/ultrasonic sensors and a removable smartphone mount. Use removable M3 adapters for payloads and maintain battery service access.

**Acceptance.** Launch the scene from its documented toolchain, place the robot at a known pose, and record a static distance target. Log a crop-row traversal and end turn with ground-truth pose, sensor timestamps, tracking error and dropouts. Release the scene sources or a reproducible generator, asset permissions, dataset metadata, configuration and replay plots.

### 7. Integrate firmware, power and a serviceable build

**Deliverables.** Define a hardware abstraction for foot targets, body pose/velocity and stop. Map each joint to its servo channel, zero, direction, PWM range and soft limit. Evaluate ESP32 and PCA9685 or a suitable alternative, and document the chosen transport, telemetry, command timeout, startup and shutdown behavior. Design controller plates for the selected Arduino, Raspberry Pi, Jetson or other footprint. Specify battery retention, accessible connectors, cable bend and moving-joint strain relief.

**Acceptance.** Publish a revisioned BOM, schematic, wiring and calibration procedure for one exact build. Measure peak and continuous current when joints move together, voltage sag, controller resets and battery runtime. Size regulator, wiring, fuse and cutoff from those measurements. Verify watchdog, undervoltage and independent emergency shutdown on a bench stand before walking trials. Check enclosure protection and serviceability for the intended field conditions.

### 8. Release evidence others can reproduce

**Deliverables.** Maintain a platform/version matrix and an issue list. For each release, publish tested assets, meshes and hashes, diagrams, source attribution, changes since the previous release, test commands, logs and known limits. Document rights for original and third-party files separately. Add a DOI or archive citation after an actual archival release exists.

**Acceptance.** A second person reproduces the mesh import, one-leg sweep and a representative benchmark from a clean checkout. Include physical measurements when a result describes hardware. For failed tests, publish the failure condition and scope. A researcher can then cite the precise revision, a student can repeat a bounded exercise, and a builder can identify the choices left for their own configuration.

## Where to contribute first

- **Students and hobbyists** can import one GLB, measure its dimensions, or print an M3 fit coupon and report the printer, material and result.
- **CAD and controls contributors** can resolve the full XML export, produce a one-leg frame map and run an independent joint sweep.
- **Research groups** can define a repeatable slope or crop-row trial and share the inputs, ground truth, metrics and failure cases.

See the [contribution guide](../CONTRIBUTING.md) for the evidence to include with each change.
