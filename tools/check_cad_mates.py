"""Explain the free (6-DOF) joints a Simscape Multibody import will create.

Simscape Multibody gives every group of parts that no mate connects to the
ground assembly its own 6-DOF Joint. This script groups the instances of an
exported assembly XML by the mates that join them and lists each floating
group, so the missing mates can be added in SOLIDWORKS before re-exporting.

    python tools/check_cad_mates.py simulation/cad-export/Full_Robot_Assembly.xml
    python tools/check_cad_mates.py simulation/cad-export/Full_Robot_Assembly.xml --strict

With --strict the script exits with status 1 while any floating group remains.
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

NS = "{urn:mathworks:SimscapeMultibody:import}"


def natural_key(name):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def analyse(xml_path):
    model = ElementTree.parse(xml_path).getroot()
    if model.tag != NS + "SimscapeMultibodyImportXML":
        raise ValueError("Expected a Simscape Multibody Import XML document")
    root = model.find(NS + "RootAssembly")
    if root is None:
        raise ValueError("Missing root assembly")
    ground = root.get("uid") or root.get("name") or "root"

    instances = [item.get("uid") for item in model.iter(NS + "Instance")]
    parent = {name: name for name in instances + [ground]}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    mates = defaultdict(list)
    constraints = model.find(".//" + NS + "Constraints")
    for constraint in list(constraints) if constraints is not None else []:
        kind = constraint.tag.replace(NS, "")
        members = [geom.findtext(NS + "InstancePath/" + NS + "Uid") for geom in constraint.findall(NS + "ConstraintGeometry")]
        members = [ground if member not in parent else member for member in members if member]
        for member in members:
            mates[member].append(kind)
        for other in members[1:]:
            parent[find(other)] = find(members[0])

    groups = defaultdict(list)
    for name in instances:
        groups[find(name)].append(name)
    grounded = groups.pop(find(ground), [])
    floating = sorted((sorted(group, key=natural_key) for group in groups.values()), key=lambda g: natural_key(g[0]))
    return instances, grounded, floating, mates


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xml", type=Path, help="Assembly XML exported by Simscape Multibody Link")
    parser.add_argument("--strict", action="store_true", help="Fail while any group of parts floats free")
    args = parser.parse_args()
    try:
        instances, grounded, floating, mates = analyse(args.xml)
    except (OSError, ElementTree.ParseError, ValueError) as error:
        parser.exit(1, f"Mate check failed: {error}\n")

    print(f"{len(instances)} instances; {len(grounded)} connected to the ground assembly:")
    print("  " + ", ".join(sorted(grounded, key=natural_key)))
    unmated = [group[0] for group in floating if len(group) == 1 and not mates.get(group[0])]
    linked = [group for group in floating if not (len(group) == 1 and not mates.get(group[0]))]
    print(f"{len(floating)} floating groups -> expect {len(floating)} additional 6-DOF Joint blocks after smimport.")
    if linked:
        print(f"{len(linked)} mated groups not attached to the chassis:")
        for group in linked:
            print("  " + " + ".join(group))
    if unmated:
        print(f"{len(unmated)} instances with no mates at all:")
        print("  " + ", ".join(unmated))
    if floating:
        print("Fix in SOLIDWORKS: fix each servo case to the part that carries it, mate each horn")
        print("axis to the next link, re-export with Simscape Multibody Link, then run this check again.")
    if args.strict and floating:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
