#!/usr/bin/env python3
"""Export visual meshes from source CAD STLs to GLB 2.0 assets for Unity/Unreal.

Reproducibly converts CAD STL parts into separate indexed standalone GLB 2.0
static meshes scaled from millimeters to meters. Coordinate basis mapping maps
STL nominal +Z up to glTF standard +Y up (using [x, z, -y]), preserving mesh
origins and topology without decimation or inference of robot forward.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh

# Relative paths anchored to project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "Printables"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "simulation" / "meshes"
DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUT_DIR / "manifest.json"

PARTS = [
    "Robot_Base",
    "LidarCover",
    "L1",
    "L2",
    "L3",
]

# Coordinate basis mapping:
# Maps STL coordinates [x_stl, y_stl, z_stl] (mm) to output coordinates [x_out, y_out, z_out] (m)
# x_out =  x_stl * 0.001
# y_out =  z_stl * 0.001
# z_out = -y_stl * 0.001
# STL +Z nominal up -> glTF +Y up. STL +Y -> glTF -Z. STL +X -> glTF +X.
BASIS_MAPPING = "[x, z, -y]"
SCALE_FACTOR = 0.001
TRANSFORM_MATRIX = np.array([
    [0.001,  0.0,    0.0,   0.0],
    [0.0,    0.0,    0.001, 0.0],
    [0.0,   -0.001,  0.0,   0.0],
    [0.0,    0.0,    0.0,   1.0],
], dtype=np.float64)


def compute_sha256(file_path: Path) -> str:
    """Compute hex-encoded SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_standalone_glb(glb_path: Path) -> tuple[bool, str]:
    """Verify that a GLB file is valid standalone GLB 2.0 without external buffers."""
    raw = glb_path.read_bytes()
    if len(raw) < 20:
        return False, "File too small for GLB header"

    magic, version, length = struct.unpack("<4sII", raw[:12])
    if magic != b"glTF":
        return False, f"Invalid magic header: {magic!r}"
    if version != 2:
        return False, f"Unsupported glTF version: {version}"
    if length != len(raw):
        return False, f"Header length mismatch: declared {length}, actual {len(raw)}"

    chunk_length, chunk_type = struct.unpack("<II", raw[12:20])
    if chunk_type != 0x4E4F534A:  # "JSON"
        return False, f"First chunk is not JSON: {chunk_type:#x}"

    try:
        json_data = json.loads(raw[20:20 + chunk_length].decode("utf-8"))
    except Exception as e:
        return False, f"Failed to parse GLB JSON chunk: {e}"

    buffers = json_data.get("buffers", [])
    for idx, buf in enumerate(buffers):
        if "uri" in buf:
            return False, f"Buffer {idx} specifies external URI: {buf['uri']}"

    # Verify indexed geometry
    meshes = json_data.get("meshes", [])
    if not meshes:
        return False, "No meshes found in GLB JSON"
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            if "indices" not in prim:
                return False, "Primitive is not indexed"

    return True, "Valid standalone indexed GLB 2.0"


def export_meshes(
    input_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> int:
    """Load STL parts, transform coordinates, and export GLB 2.0 assets and manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_meshes = {}

    print(f"Exporting meshes from {input_dir} to {output_dir}...")
    for part in PARTS:
        stl_path = input_dir / f"{part}.STL"
        glb_path = output_dir / f"{part}.glb"

        if not stl_path.exists():
            print(f"ERROR: Source file not found: {stl_path}", file=sys.stderr)
            return 1

        input_hash = compute_sha256(stl_path)

        # Load STL geometry
        mesh = trimesh.load(str(stl_path), file_type="stl")
        triangle_count = int(len(mesh.faces))

        # Apply basis transformation (scaling mm to m and basis mapping [x, z, -y])
        mesh.apply_transform(TRANSFORM_MATRIX)

        bounds_min = [float(val) for val in mesh.bounds[0]]
        bounds_max = [float(val) for val in mesh.bounds[1]]

        # Export to standalone indexed GLB 2.0
        glb_data = mesh.export(file_type="glb")
        glb_path.write_bytes(glb_data)

        output_hash = compute_sha256(glb_path)

        # Validate standalone GLB structure
        ok, msg = verify_standalone_glb(glb_path)
        if not ok:
            print(f"ERROR: Exported GLB validation failed for {part}: {msg}", file=sys.stderr)
            return 1

        rel_source = stl_path.relative_to(PROJECT_ROOT).as_posix()
        rel_output = glb_path.relative_to(PROJECT_ROOT).as_posix()

        manifest_meshes[part] = {
            "source_file": rel_source,
            "output_file": rel_output,
            "input_sha256": input_hash,
            "output_sha256": output_hash,
            "triangle_count": triangle_count,
            "output_bounds_m": {
                "min": bounds_min,
                "max": bounds_max,
            },
        }

        print(
            f"  {part:12s} -> {triangle_count:6d} tris | "
            f"bounds: min={bounds_min}, max={bounds_max}"
        )

    manifest_data = {
        "coordinate_mapping": {
            "basis_mapping": BASIS_MAPPING,
            "scale": SCALE_FACTOR,
            "unit_in": "mm",
            "unit_out": "m",
            "description": (
                "Interchange coordinates mapping STL nominal +Z up to glTF standard +Y up. "
                "x_out = x_stl * 0.001, y_out = z_stl * 0.001, z_out = -y_stl * 0.001. "
                "Robot forward is not inferred. Mesh origins preserved."
            ),
            "transform_matrix_4x4": TRANSFORM_MATRIX.tolist(),
        },
        "meshes": manifest_meshes,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


def check_meshes(
    input_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> int:
    """Verify source and output assets against manifest without modifying files."""
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Failed to read manifest: {e}", file=sys.stderr)
        return 1

    meshes_meta = manifest.get("meshes", {})
    if not meshes_meta:
        print("ERROR: No meshes defined in manifest", file=sys.stderr)
        return 1

    all_passed = True
    print(f"Checking assets against manifest ({manifest_path.name})...")

    for part in PARTS:
        if part not in meshes_meta:
            print(f"ERROR: Part '{part}' missing from manifest", file=sys.stderr)
            all_passed = False
            continue

        meta = meshes_meta[part]
        stl_path = input_dir / f"{part}.STL"
        glb_path = output_dir / f"{part}.glb"
        if (meta["source_file"] != stl_path.relative_to(PROJECT_ROOT).as_posix()
                or meta["output_file"] != glb_path.relative_to(PROJECT_ROOT).as_posix()):
            print(f"ERROR: [{part}] Manifest paths differ from the expected paths", file=sys.stderr)
            all_passed = False
            continue

        if not stl_path.exists():
            print(f"ERROR: [{part}] Source STL missing: {stl_path}", file=sys.stderr)
            all_passed = False
            continue
        if not glb_path.exists():
            print(f"ERROR: [{part}] Output GLB missing: {glb_path}", file=sys.stderr)
            all_passed = False
            continue

        # Check hashes
        source_hash = compute_sha256(stl_path)
        if source_hash != meta["input_sha256"]:
            print(f"ERROR: [{part}] Source SHA256 mismatch: {source_hash} != {meta['input_sha256']}", file=sys.stderr)
            all_passed = False

        output_hash = compute_sha256(glb_path)
        if output_hash != meta["output_sha256"]:
            print(f"ERROR: [{part}] Output SHA256 mismatch: {output_hash} != {meta['output_sha256']}", file=sys.stderr)
            all_passed = False

        # Verify standalone GLB container
        ok, msg = verify_standalone_glb(glb_path)
        if not ok:
            print(f"ERROR: [{part}] GLB container check failed: {msg}", file=sys.stderr)
            all_passed = False

        # Check geometry counts and dimensions
        src_mesh = trimesh.load(str(stl_path), file_type="stl")
        src_tri_count = len(src_mesh.faces)
        if src_tri_count != meta["triangle_count"]:
            print(f"ERROR: [{part}] Source triangle count mismatch: {src_tri_count} != {meta['triangle_count']}", file=sys.stderr)
            all_passed = False

        glb_scene = trimesh.load(str(glb_path), file_type="glb")
        if isinstance(glb_scene, trimesh.Scene):
            glb_mesh = glb_scene.to_geometry()
        else:
            glb_mesh = glb_scene

        glb_tri_count = len(glb_mesh.faces)
        if glb_tri_count != meta["triangle_count"]:
            print(f"ERROR: [{part}] GLB triangle count mismatch: {glb_tri_count} != {meta['triangle_count']}", file=sys.stderr)
            all_passed = False

        # Verify bounds match manifest and transformed STL
        src_mesh.apply_transform(TRANSFORM_MATRIX)
        expected_bounds = src_mesh.bounds
        manifest_min = np.array(meta["output_bounds_m"]["min"])
        manifest_max = np.array(meta["output_bounds_m"]["max"])
        glb_bounds = glb_mesh.bounds

        # Floating point tolerance: 1e-5 meters (0.01 mm)
        tol = 1e-5
        if not np.allclose(glb_bounds[0], manifest_min, atol=tol):
            print(f"ERROR: [{part}] GLB bounds min mismatch vs manifest: {glb_bounds[0]} vs {manifest_min}", file=sys.stderr)
            all_passed = False
        if not np.allclose(glb_bounds[1], manifest_max, atol=tol):
            print(f"ERROR: [{part}] GLB bounds max mismatch vs manifest: {glb_bounds[1]} vs {manifest_max}", file=sys.stderr)
            all_passed = False
        if not np.allclose(glb_bounds, expected_bounds, atol=tol):
            print(f"ERROR: [{part}] GLB bounds mismatch vs transformed source: diff={np.max(np.abs(glb_bounds - expected_bounds))}", file=sys.stderr)
            all_passed = False

        print(f"  Checked {part}: {glb_tri_count} triangles")

    if all_passed:
        print("All asset checks passed successfully.")
        return 0
    else:
        print("Asset checks failed.", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export CAD STLs to GLB 2.0 visual meshes for Unity/Unreal."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify source/output assets and manifest integrity without altering files",
    )

    args = parser.parse_args()

    if args.check:
        return check_meshes(DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_MANIFEST_PATH)
    else:
        return export_meshes(DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_MANIFEST_PATH)


if __name__ == "__main__":
    sys.exit(main())
