# Simulation and engine interchange

Start with the visual meshes to study packaging, or run the MATLAB leg example to explore a static load. The [engineering roadmap](development-roadmap.md) describes the additional work for a calibrated six-legged robot.

| Workflow | What you can run or inspect | Validation status |
| --- | --- | --- |
| SOLIDWORKS | Full CAD assembly and leg subassembly | Main assembly opened in SOLIDWORKS 2025. The separate leg file may request a rebuild. |
| Blender | Import the five GLB files individually | All five imported in Blender 4.2.16 LTS. Triangle counts and physical extents matched the source conversion. |
| Unity | Import the same GLBs with Unity glTFast | Documented static-asset workflow. Native editor test pending. |
| Unreal Engine | Import the same GLBs as static meshes | Documented static-asset workflow. Native editor and co-simulation tests pending. |
| MATLAB | Calculate idealized one-leg position, Jacobian and holding torque | Two tests passed on MATLAB R2025b, including a finite-difference check. |
| Simscape Multibody | Full assembly XML and seven STEP files | Imported and compiled in R2025b. The generated model contains 18 revolute joints and 29 additional 6-DOF joints. |

## Visual meshes

Download [Robot_Base.glb](../simulation/meshes/Robot_Base.glb) for a first import. The [mesh directory](../simulation/meshes/) also contains L1, L2, L3 and the LiDAR cover. These are standalone, full-resolution meshes of individual printed parts. A scene containing the assembled robot will need assembly transforms, joint frames, simplified collision shapes and inertial properties.

The GLBs use meters. For interchange, STL coordinates in millimeters are transformed as `(x, z, −y) × 0.001`. This preserves each source origin and treats the exported STL's positive Z as nominal up. The robot's physical forward direction and joint axes still require calibration in assembly coordinates. The chassis's longest dimension should measure approximately **0.2089 m**, or **20.89 cm**, in any importer.

**Unity.** Create a 3D project and install the version of Unity glTFast compatible with your editor through Package Manager. Copy the GLB into the project's Assets folder. Drag the imported model into a scene at unit scale, inspect the bounds, and record the package and editor versions. Repeat for one leg link before assembling a prefab. [Unity glTFast documentation](https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.12/manual/index.html)

**Unreal Engine.** Use **Import** in the Content Browser to load the GLB as a static mesh. Place the asset into an empty level at actor scale one. Check its longest span in centimeters, inspect normals, and record the importer settings. Use simpler collision proxies when you begin physics experiments. [Epic Games glTF import guide for Unreal Engine 5.3](https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-gltf-files-into-unreal-engine?application_version=5.3)

**Rebuild or check the files.** From the repository root, use Python 3.12 with NumPy and trimesh. The commands below use the versions exercised for this publication. The manifest records source and output SHA-256 hashes, triangle counts, scale, basis and bounds. [Mesh manifest](../simulation/meshes/manifest.json)

```sh
python -m pip install -r tools/mesh-requirements.txt
python tools/export_visual_meshes.py --check
python tools/export_visual_meshes.py
```

## Single-leg static study

The MATLAB example models one ideal yaw–pitch–pitch chain. Supply three lengths in meters, three angles in radians and an external foot force in newtons expressed in the hip frame. The calculated torque balances that external force in static equilibrium. Link weight, inertia, contact dynamics, friction and actuator losses require additional modeling. The lengths and load below are illustrative inputs and should be replaced with measured values for design work.

From the repository root in MATLAB:

```matlab
addpath('simulation/matlab')
lengths = [0.03; 0.10; 0.12];
angles = [0; 0; 0];
tipForce = [0; 0; -5];
[footPosition, J, holdingTorque] = legStaticStudy(lengths, angles, tipForce);
assertSuccess(runtests('simulation/matlab/testLegStaticStudy.m'))
```

For this example the foot is **0.25 m** along positive X. The balancing joint torques are **0, 1.10 and 0.60 N·m**. The straight-leg result is a moment-arm check. A second test estimates each Jacobian column numerically at a bent configuration. These results apply to the example inputs. They cannot establish the suitability of an MG996R servo for the robot.

## Full robot and agricultural scene

Run this check from the repository root to confirm that the XML parses and all seven referenced STEP files are present.

```sh
python tools/check_cad_export.py simulation/cad-export/Full_Robot_Assembly.xml
```

Copy the contents of [simulation/cad-export](../simulation/cad-export/) to a writable working directory and make it the current MATLAB folder. To reproduce the import and count the joint blocks in R2025b:

```matlab
model = smimport('Full_Robot_Assembly.xml');
name = get_param(model,'Name');
set_param(name,'SimulationCommand','update');
revolute = find_system(name,'ReferenceBlock','sm_lib/Joints/Revolute Joint');
free = find_system(name,'ReferenceBlock','sm_lib/Joints/6-DOF Joint');
disp([numel(revolute), numel(free)])   % Observed: 18, 29
```

The generated parameter file associates twelve revolute joints with the six L1 links and six with the six L3 links. The additional 6-DOF joints require a mechanical review. Trace each one to its connected bodies, check which connections should be rigid, and compare the remaining joint axes with the assembled hardware before using the model for gait or torque estimates. [Joint acceptance test](development-roadmap.md#2-establish-one-leg-then-all-18-leg-axes) · [MathWorks model import](https://www.mathworks.com/help/sm/ref/smimport.html)

The development machine reported MATLAB R2025b with Simulink, Simscape Multibody, Multibody Link and Robotics System Toolbox. The installed support-package inventory listed Arduino packages only. For the agricultural scene, MathWorks pairs R2025b with **Unreal Engine 5.3** and requires its **Robotics System Toolbox Interface for Unreal Engine Projects** for custom scenes. On Windows, confirm a supported Visual Studio 2022 C++ toolchain before building the project. The first scene milestone is one crop row, one known robot pose and one sensor target. [MathWorks compatibility table](https://www.mathworks.com/help/robotics/ug/unreal-engine-simulation-environment-requirements-and-limitations.html)
