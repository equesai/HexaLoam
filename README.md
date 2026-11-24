# HexaLoam — 3D-Printable Hexapod Robot Platform with LiDAR

**HexaLoam is a modifiable six-legged robot (hexabot) platform** for agriculture, inspection, mapping, education, and robotics research. The repository provides editable SOLIDWORKS CAD and 3D-print files for the chassis, six leg sets, and LiDAR cover. The reference assembly shows MG996R servos and an RP-Lidar sensor on the chassis.

Published by **HexaLoam contributors**.

![Isometric SOLIDWORKS render of the HexaLoam hexapod with six legs around a central chassis](docs/assembly-preview.png)

This is a **mechanical starting point**. The designer is expected to finish the robot around the intended application, including the payload, mounting adapters, actuators, controller, battery, wiring, firmware, and validation.

[Designer guide and examples](docs/designer-guide.md) · [Main SOLIDWORKS assembly](Full_Robot_Assembly.SLDASM) · [STL and 3MF print files](Printables/)

## Example applications

| Field | Example project | What the designer would add |
| --- | --- | --- |
| Agricultural robotics | Greenhouse or crop-row scouting | A camera or environmental sensor, a protective mount, and clearance for plants and soil |
| Inspection | Visual checks in a workshop or equipment aisle | A camera, lighting, and a mount that keeps the payload clear of the legs |
| Mapping | Indoor LiDAR scanning and mapping experiments | A controller or onboard computer, sensor integration, and mapping software |
| Education | A classroom hexapod for studying gait and kinematics | A controller, servo power, and firmware for repeatable gait exercises |
| Robotics research | Comparing locomotion on different surfaces | An IMU or other instrumentation, data logging, and repeatable test setups |

These are example configurations for designing a build. The repository contains mechanical files and CAD reference components. Firmware, wiring, a complete purchasing bill of materials, and field-test results are outside its current scope.

## Adapt the chassis

The base is **controller-agnostic** by design. Its central area provides room to place a controller and batteries selected for the application. Multiple mounting holes and pockets for **M3 nuts** give designers options for attaching brackets, adapter plates, covers, and payloads. Choose the mounting locations that suit your layout, then check the actual controller, battery, and fastener dimensions in CAD before printing.

![Isometric SOLIDWORKS render of the chassis showing the central equipment area, mounting holes, and nut pockets](docs/chassis-isometric.png)

The reference CAD locates an RP-Lidar model on the chassis and includes an editable cover. Designers can adapt the mount for their own sensor and verify its field of view and cable clearance. See the [designer guide](docs/designer-guide.md) for mounting and integration steps.

## Which parts are 3D printable?

The files cover the **custom printed structure**. Five STL designs make up 20 printed pieces for one robot. A working build also needs separate servos, fasteners, a controller, batteries and power hardware, and any chosen sensors.

| Part | Quantity | Approximate STL dimensions (X × Y × Z, mm) |
| --- | ---: | --- |
| [Robot base](Printables/Robot_Base.STL) | 1 | 203.5 × 68.0 × 208.9 |
| [Leg link L1](Printables/L1.STL) | 6 | 119.9 × 123.0 × 120.0 |
| [Leg link L2](Printables/L2.STL) | 6 | 158.6 × 64.8 × 39.4 |
| [Leg link L3](Printables/L3.STL) | 6 | 246.2 × 50.0 × 120.0 |
| [LiDAR cover](Printables/LidarCover.STL) | 1 | 111.3 × 63.0 × 77.5 |

The five STL meshes are watertight and consistently wound. The dimensions describe each part in its exported orientation. Review how rotation, supports, and adhesion affect the build volume for your printer.

## Print the parts

1. Open [Full_Robot.3mf](Printables/Full_Robot.3mf) in Bambu Studio. The file contains six plate layouts and a Bambu Lab X1 Carbon profile with a 0.4 mm nozzle.
2. Select your printer and material profile, then check orientation, supports, and printability. L3 measures about 246 mm along its longest exported axis.
3. For another slicer, import the [individual STLs](Printables/) in millimeters and use the quantities above.
4. Print one leg set and check the fit with your actual hardware before printing the remaining five.

## Open and inspect the CAD

1. Clone the repository or download its ZIP from GitHub's **Code** menu, keeping the folder layout intact.
2. Open [Full_Robot_Assembly.SLDASM](Full_Robot_Assembly.SLDASM) in SOLIDWORKS. Use [LegMates.SLDASM](LegMates.SLDASM) to inspect a single leg. The leg assembly may prompt for a rebuild.
3. Look in [Designed/](Designed/) for the editable robot parts and [Common/](Common/) for the servo, LiDAR, and battery reference models if SOLIDWORKS prompts for references.

The repository includes all dependencies reported for the main robot and leg assemblies. The separate 4S3P 18650 battery reference assembly expects `18650 cells Spacers.step.SLDPRT`, which is absent from the source folder. The main robot assembly opens independently of that reference assembly.

## MATLAB and Simscape Multibody analysis

The simulation design target is **18 revolute joints and 18 leg degrees of freedom**, with three single-axis joints per leg. The intended workflow is to import the assembly XML and its companion geometry into MATLAB and Simscape Multibody, then configure joint actuation and sensing to analyze angular position, speed, and required actuator torque for the intended gait and payload. A complete import with the expected joint count still needs verification. See the [simulation plan](docs/designer-guide.md#simulation-plan).

## Supporting CAD

The battery and LiDAR CAD files came from the `18650-li-ion-battery-6` and `rp-lidar-2` reference collections. The MG996R servo model came from the project team's reference CAD. The repository has no blanket open-source license.
