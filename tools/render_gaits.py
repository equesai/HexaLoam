"""Render CAD-based walking demonstrations from the gait generator's pose files."""

import argparse
import math
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import vtk
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from PIL import Image, ImageDraw, ImageFont
from vtk.util.numpy_support import vtk_to_numpy

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "simulation/cad-export"
CAD = ET.parse(EXPORT / "Full_Robot_Assembly.xml").getroot()
PALETTE = {"Robot_Base": "d79a36", "L1": "b8c4c8", "L2": "e1e3df", "L3": "9caeb5",
           "Servo Motor MG996R": "33404d", "LidarCover": "d7a044", "RP-Lidar": "397878"}
GAITS = {"tripod": ("Tripod", "Two alternating groups", "3 feet in stance"),
         "ripple": ("Ripple", "Overlapping swing phases", "4 feet in stance"),
         "wave": ("Wave", "One foot lifts at a time", "5 feet in stance")}
SWING_COLOR = "#d98a24"
STANCE_COLOR = "#307a74"


def rgb(hex_color):
    return tuple(x / 255 for x in bytes.fromhex(hex_color.lstrip("#")))


def load_shapes(cache):
    """Tessellate the seven STEP files once; share each mesh between its instances."""
    cache.mkdir(parents=True, exist_ok=True)
    mappers = {}
    for part in CAD.findall(".//{*}Part"):
        name = part.get("name")
        step = EXPORT / part.find("{*}GeometryFile").get("name")
        stl = cache / (name + ".stl")
        if not stl.exists() or stl.stat().st_mtime < step.stat().st_mtime:
            reader = STEPControl_Reader()
            if reader.ReadFile(str(step)) != IFSelect_RetDone:
                raise ValueError(f"Cannot load {step.name}")
            reader.TransferRoots()
            shape = reader.OneShape()
            mesh = BRepMesh_IncrementalMesh(shape, 0.18, False, 0.28, True)
            writer = StlAPI_Writer()
            writer.ASCIIMode = False
            if not mesh.IsDone() or not writer.Write(shape, str(stl)):
                raise ValueError(f"Cannot tessellate {step.name}")
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(stl))
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputConnection(reader.GetOutputPort())
        normals.SetFeatureAngle(32)
        normals.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(normals.GetOutput())
        mappers[part.get("uid")] = (name, mapper)
    return mappers


def add_grid(renderer, ground):
    points, lines = vtk.vtkPoints(), vtk.vtkCellArray()
    for n in range(-20, 21):
        v = n * 0.05
        for start, end in [((v,ground,-1),(v,ground,1)), ((-1,ground,v),(1,ground,v))]:
            a, b = points.InsertNextPoint(*start), points.InsertNextPoint(*end)
            lines.InsertNextCell(2)
            lines.InsertCellPoint(a)
            lines.InsertCellPoint(b)
    data = vtk.vtkPolyData()
    data.SetPoints(points)
    data.SetLines(lines)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(data)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(.63,.70,.72)
    actor.GetProperty().SetOpacity(.32)
    renderer.AddActor(actor)


def font(size, bold=False):
    for face in (("DejaVuSans-Bold.ttf", "segoeuib.ttf") if bold else ("DejaVuSans.ttf", "segoeui.ttf")):
        try:
            return ImageFont.truetype(face, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def render(gait, poses, destination, mappers, ffmpeg):
    names, labels = poses["names"].tolist(), poses["leg_names"].tolist()
    transforms, swing, feet = poses["transforms"], poses["swing"], poses["feet"]
    ground = float(feet[:,:,1].min()) - .025
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.88,.92,.93)
    renderer.SetBackground2(.99,.99,.98)
    renderer.GradientBackgroundOn()
    add_grid(renderer, ground)
    by_uid = {i.get("uid"): i.get("entityUid") for i in CAD.findall(".//{*}Instance")}
    actors = []
    for uid in names:
        part_name, mapper = mappers[by_uid[uid]]
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        material = actor.GetProperty()
        material.SetColor(*rgb(PALETTE[part_name]))
        material.SetInterpolationToPhong()
        material.SetAmbient(.20)
        material.SetSpecular(.23)
        material.SetSpecularPower(32)
        renderer.AddActor(actor)
        actors.append(actor)
    feet_by_uid = {f"L3-{i}": labels.index(lab) for i,lab in enumerate(["LM","LR","RR","RM","RF","LF"],2)}
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(968,720)
    win.SetMultiSamples(4)
    win.AddRenderer(renderer)
    cam = renderer.GetActiveCamera()
    focus = np.array([-.055 + (poses["body_x"][0]+poses["body_x"][-1])/2,ground+.12,-.005])
    cam.SetFocalPoint(*focus)
    cam.SetPosition(*(focus+np.array([.38,.58,1.04])))
    cam.SetViewUp(0,1,0)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(.335)
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(win)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()
    panel = Image.new("RGB", (312,720), "#f7f7f2")
    draw = ImageDraw.Draw(panel)
    ink = "#20353a"
    title, subtitle, supports = GAITS[gait]
    draw.text((24,51), title, font=font(42,True), fill=ink)
    draw.text((24,115), subtitle, font=font(18), fill=ink)
    draw.text((24,147), supports, font=font(18,True), fill=ink)
    draw.line((24,201,288,201), fill="#c4ceca", width=2)
    draw.text((24,224), "Footfall diagram", font=font(21,True), fill=ink)
    draw.text((124,273), "FRONT", font=font(15,True), fill=ink)
    draw.rounded_rectangle((129,316,183,460), radius=20, fill="#dce4de", outline="#9daea7", width=2)
    locations = {label:(85 if label[0]=="L" else 227, {"F":330,"M":388,"R":446}[label[1]]) for label in labels}
    for label,(x,y) in locations.items():
        draw.line((x,y,156,y), fill="#aebeb8", width=3)
        draw.text((x-40 if label[0]=="L" else x+17,y-11),label,font=font(16,True),fill=ink)
    for y, color, label in [(523,STANCE_COLOR,"Stance"),(565,SWING_COLOR,"Swing")]:
        draw.ellipse((25,y,43,y+18), fill=color)
        draw.text((56,y-3),label,font=font(18),fill=ink)
    draw.text((24,655),"Kinematic demonstration",font=font(16),fill=ink)
    scale = np.diag([.001,.001,.001,1.0])
    command = [ffmpeg,"-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","1280x720",
               "-r",str(int(poses.get("fps",24))),"-i","-","-an","-c:v","libx264","-crf","18","-pix_fmt","yuv420p",
               "-movflags","+faststart",str(destination)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as proc:
        for frame, matrices in enumerate(transforms):
            for uid, actor, matrix in zip(names,actors,matrices):
                vtk_matrix = vtk.vtkMatrix4x4()
                vtk_matrix.DeepCopy((matrix @ scale).ravel().tolist())
                actor.SetUserMatrix(vtk_matrix)
                if uid in feet_by_uid:
                    active = swing[frame,feet_by_uid[uid]]
                    actor.GetProperty().SetColor(*rgb(SWING_COLOR if active else STANCE_COLOR))
            renderer.ResetCameraClippingRange()
            win.Render()
            capture.Modified()
            capture.Update()
            pixels = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars())
            left = Image.fromarray(np.flipud(pixels.reshape(720,968,3)).copy())
            image = Image.new("RGB",(1280,720))
            image.paste(left)
            image.paste(panel,(968,0))
            overlay = ImageDraw.Draw(image)
            for label, active in zip(labels,swing[frame]):
                x,y = locations[label]
                x += 968
                overlay.ellipse((x-10,y-10,x+10,y+10),fill=SWING_COLOR if active else STANCE_COLOR)
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(f"FFmpeg failed to encode {destination.name}")
    win.Finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poses",required=True,type=Path)
    parser.add_argument("--cache",required=True,type=Path,help="Writable tessellation cache directory")
    parser.add_argument("--output",type=Path,default=ROOT/"docs/media")
    parser.add_argument("--ffmpeg",default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error("Provide --ffmpeg or put FFmpeg on PATH")
    args.output.mkdir(parents=True,exist_ok=True)
    shapes = load_shapes(args.cache)
    for gait in GAITS:
        with np.load(args.poses / f"{gait}.npz", allow_pickle=False) as poses:
            render(gait,dict(poses),args.output / f"gait-{gait}.mp4",shapes,args.ffmpeg)
