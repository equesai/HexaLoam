"""Check a portable Simscape Multibody XML export before importing it in MATLAB."""

import argparse
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree


def check_export(xml_path):
    model = ElementTree.parse(xml_path).getroot()
    namespace = "{urn:mathworks:SimscapeMultibody:import}"
    if model.tag != namespace + "SimscapeMultibodyImportXML":
        raise ValueError("Expected a Simscape Multibody Import XML document")
    assembly = model.find(namespace + "RootAssembly")
    if assembly is None or assembly.find(namespace + "InstanceTree") is None:
        raise ValueError("Missing root assembly or instance tree")

    folder = xml_path.resolve().parent
    geometry = {item.get("name", "") for item in model.iter(namespace + "GeometryFile")}
    if not geometry:
        raise ValueError("No companion geometry files listed")
    for name in sorted(geometry):
        reference = PureWindowsPath(name)
        path = folder.joinpath(*reference.parts).resolve()
        if reference.anchor or not path.is_relative_to(folder) or not path.is_file():
            raise ValueError(f"Missing or nonportable geometry reference: {name!r}")
    print(f"XML parsed and {len(geometry)} companion geometry files found.")
    print("Next, import in MATLAB and independently test the motion of each joint.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path, help="Assembly XML exported with companion geometry")
    try:
        check_export(parser.parse_args().xml)
    except (OSError, ElementTree.ParseError, ValueError) as error:
        parser.exit(1, f"Export check failed: {error}\n")
