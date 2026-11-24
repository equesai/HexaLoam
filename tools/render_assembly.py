"""Render the assembled CAD pose as a turntable and four orthographic stills."""

import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import vtk
from PIL import Image
from scipy.spatial import ConvexHull
from vtk.util.numpy_support import vtk_to_numpy

from render_gaits import CAD, PALETTE, ROOT, load_shapes, rgb

WIDTH, HEIGHT = 1280, 720


def assembly_scene(cache):
    shapes = load_shapes(cache)
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.87, .91, .93)
    renderer.SetBackground2(.99, .99, .985)
    renderer.GradientBackgroundOn()
    renderer.AutomaticLightCreationOff()
    headlight = vtk.vtkLight()
    headlight.SetLightTypeToHeadlight()
    renderer.AddLight(headlight)
    for direction, intensity in [((-.6, .9, .7), .87), ((.7, .2, -.8), .48),
                                 ((.1, -.75, .7), .40)]:
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*direction)
        light.SetFocalPoint(-.055, -.085, -.005)
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    hulls = {}
    points = []
    for instance in CAD.findall(".//{*}Instance"):
        key = instance.get("entityUid")
        name, mapper = shapes[key]
        rotation = np.fromstring(instance.findtext(".//{*}Rotation"), sep=" ").reshape(3, 3)
        origin = np.fromstring(instance.findtext(".//{*}Translation"), sep=" ")
        transform = np.eye(4)
        transform[:3, :3] = rotation * .001
        transform[:3, 3] = origin
        matrix = vtk.vtkMatrix4x4()
        matrix.DeepCopy(transform.ravel().tolist())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.SetUserMatrix(matrix)
        material = actor.GetProperty()
        material.SetColor(*rgb(PALETTE[name]))
        material.SetInterpolationToPhong()
        material.SetAmbient(.23)
        material.SetDiffuse(.78)
        material.SetSpecular(.27)
        material.SetSpecularPower(40)
        renderer.AddActor(actor)
        if key not in hulls:
            vertices = vtk_to_numpy(mapper.GetInput().GetPoints().GetData()).astype(float)
            hulls[key] = vertices[ConvexHull(vertices).vertices] * .001
        points.append(hulls[key] @ rotation.T + origin)
    return renderer, np.vstack(points)


def camera_pose(points, yaw, elevation):
    az, el = np.radians([yaw, elevation])
    toward = np.array([math.cos(el)*math.sin(az), math.sin(el), math.cos(el)*math.cos(az)])
    right = np.array([math.cos(az), 0., -math.sin(az)])
    up = np.cross(toward, right)
    basis = np.column_stack([right, up, toward])
    projected = points @ basis
    low, high = projected.min(axis=0), projected.max(axis=0)
    center = basis @ ((low+high)/2)
    span = high-low
    scale = .5*max(span[1], span[0]*HEIGHT/WIDTH)/.84
    return center, toward, up, scale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--output", type=Path, default=ROOT/"docs/media")
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error("Supply --ffmpeg or put FFmpeg on PATH")
    args.output.mkdir(exist_ok=True, parents=True)
    renderer, points = assembly_scene(args.cache)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(WIDTH, HEIGHT)
    window.SetMultiSamples(4)
    window.AddRenderer(renderer)
    camera = renderer.GetActiveCamera()
    camera.ParallelProjectionOn()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()

    def frame(pose, overhead=False):
        center, toward, up, scale = pose
        for light in renderer.GetLights():
            light.SetSwitch(overhead != bool(light.LightTypeIsHeadlight()))
        camera.SetPosition(*(center+toward))
        camera.SetFocalPoint(*center)
        camera.SetViewUp(*up)
        camera.SetParallelScale(scale)
        renderer.ResetCameraClippingRange()
        window.Render()
        capture.Modified()
        capture.Update()
        raw = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars())
        return np.flipud(raw.reshape(HEIGHT, WIDTH, 3)).copy()

    for label, yaw, elevation in (("hero", 36, 27), ("top", 90, 90),
                                  ("profile", 10, 3), ("underside", 136, -46)):
        Image.fromarray(frame(camera_pose(points, yaw, elevation), label == "top")).save(
            args.output/f"assembly-{label}.png", optimize=True)
    poses = [camera_pose(points, 36+360*i/168, 26) for i in range(168)]
    fixed_scale = max(pose[3] for pose in poses)
    video = args.output/"assembly-orbit.mp4"
    cmd = [args.ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{WIDTH}x{HEIGHT}", "-r", "24", "-i", "-", "-an", "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(video)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        for center, toward, up, _ in poses:
            proc.stdin.write(frame((center, toward, up, fixed_scale)).tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("Turntable encoding failed")
    window.Finalize()
    filt = ("fps=12,scale=640:-1:flags=lanczos,split[a][b];"
            "[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4")
    subprocess.run([args.ffmpeg, "-y", "-v", "error", "-i", str(video), "-filter_complex",
                    filt, "-loop", "0", str(args.output/"assembly-orbit.gif")], check=True)


if __name__ == "__main__":
    main()
