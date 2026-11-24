# HexaLoam

HexaLoam is a six-legged agricultural robot prototype. This repository contains its mechanical design in SOLIDWORKS, supporting component models, and 3D-print exports for the chassis, leg links, and LiDAR cover.

![Isometric SOLIDWORKS preview of the six-legged robot assembly](docs/assembly-preview.png)

## Repository contents

| File or directory | Contents |
| --- | --- |
| [Full_Robot_Assembly.SLDASM](Full_Robot_Assembly.SLDASM) | Top-level robot assembly |
| [LegMates.SLDASM](LegMates.SLDASM) | Leg subassembly with mates |
| [Designed/](Designed/) | Editable models for the base, LiDAR cover, and three leg links |
| [Common/](Common/) | Supporting CAD for the MG996R servo, RP-Lidar, and a 4S3P 18650 battery reference assembly |
| [Printables/](Printables/) | Five individual STL meshes and a six-plate Bambu Studio project |

## Open the mechanical design

1. Clone the repository or download its ZIP from GitHub.
2. Keep the folder layout intact and open `Full_Robot_Assembly.SLDASM` in SOLIDWORKS.
3. If SOLIDWORKS prompts for a component, resolve it from `Designed/` or `Common/` before rebuilding the assembly.

The repository contains all file dependencies reported for the main robot and leg assemblies. SOLIDWORKS may request a rebuild when opening `LegMates.SLDASM`. The separate battery reference assembly expects `18650 cells Spacers.step.SLDPRT`, which is absent from the source folder. The main robot assembly does not reference the battery assembly.

## Prepare the printed parts

Open [Full_Robot.3mf](Printables/Full_Robot.3mf) in Bambu Studio to inspect the existing layouts. The six plates contain one base, one LiDAR cover, and six copies each of leg links L1, L2, and L3. For another slicer, import the individual STLs from [Printables/](Printables/) in millimeters and arrange the parts for your printer. Review material, supports, orientation, and fit before printing a full set.

## Prototype scope

The CAD models describe the mechanical design and component placement. Firmware, gait control, wiring, a procurement bill of materials, and field-test results are outside the scope of this repository.

## Supporting CAD

The battery and LiDAR CAD files were carried over from the `18650-li-ion-battery-6` and `rp-lidar-2` reference collections. The MG996R servo model came from the project team's reference CAD. These files are included so readers can inspect the assembly. The repository has no blanket open-source license.
