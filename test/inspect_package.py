#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

EXPECTED_STEAM_ASSETS = {
    "steam/managed/Facepunch.Steamworks.Win64.dll",
    "steam/managed/Facepunch.Steamworks.Posix.dll",
    "steam/native/win-x64/steam_api64.dll",
    "steam/native/linux-x64/libsteam_api.so",
    "steam/native/osx/libsteam_api.dylib",
}
REQUIRED_FILES = EXPECTED_STEAM_ASSETS | {
    "README.nuget.md",
    "THIRD-PARTY-NOTICES.md",
    "build/BoilerAutoInit.cs",
    "build/ThatRatDev.Steam.Boiler.props",
    "build/ThatRatDev.Steam.Boiler.targets",
    "lib/net8.0/ThatRatDev.Steam.Boiler.dll",
}


class PackageError(RuntimeError):
    pass


def child_text(parent: ET.Element, name: str) -> str:
    child = parent.find(f"{{*}}{name}")
    return "" if child is None or child.text is None else child.text.strip()


def inspect_package(path: Path, expected_version: str, expected_commit: str) -> str:
    if not path.is_file():
        raise PackageError(f"package does not exist: {path}")

    with zipfile.ZipFile(path) as package:
        archive_names = [name.rstrip("/") for name in package.namelist() if not name.endswith("/")]
        duplicates = sorted(name for name, count in Counter(archive_names).items() if count > 1)
        if duplicates:
            raise PackageError("duplicate package path: " + ", ".join(duplicates))
        names = set(archive_names)
        missing = REQUIRED_FILES - names
        if missing:
            raise PackageError("missing package files: " + ", ".join(sorted(missing)))

        notices = package.read("THIRD-PARTY-NOTICES.md").decode("utf-8")
        if "Copyright (c) 2016 Facepunch Studios LTD" not in notices:
            raise PackageError("Facepunch copyright notice is missing")
        if "Steamworks SDK Access Agreement" not in notices:
            raise PackageError("Valve redistributable terms are missing")

        steam_assets = {name for name in names if name.startswith("steam/")}
        unexpected = steam_assets - EXPECTED_STEAM_ASSETS
        if unexpected:
            raise PackageError("unexpected Steam assets: " + ", ".join(sorted(unexpected)))
        if steam_assets != EXPECTED_STEAM_ASSETS:
            raise PackageError("Steam asset set does not match the pinned release layout")

        nuspecs = [name for name in names if name.endswith(".nuspec")]
        if len(nuspecs) != 1:
            raise PackageError(f"expected one nuspec, found {len(nuspecs)}")
        metadata = ET.fromstring(package.read(nuspecs[0])).find("{*}metadata")
        if metadata is None:
            raise PackageError("nuspec metadata is missing")

    expected = {
        "id": "ThatRatDev.Steam.Boiler",
        "version": expected_version,
        "projectUrl": "https://github.com/ThatRatDev/Boiler",
        "license": "MIT",
    }
    for name, value in expected.items():
        actual = child_text(metadata, name)
        if actual != value:
            raise PackageError(f"nuspec {name} is {actual!r}, expected {value!r}")

    repository = metadata.find("{*}repository")
    if repository is None:
        raise PackageError("repository metadata is missing")
    if repository.attrib.get("type") != "git":
        raise PackageError("repository type must be git")
    if repository.attrib.get("url") != "https://github.com/ThatRatDev/Boiler.git":
        raise PackageError("repository URL is incorrect")
    if repository.attrib.get("commit") != expected_commit:
        raise PackageError("repository commit does not match the packed revision")

    return "\n".join(sorted(REQUIRED_FILES))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Boiler package metadata and assets.")
    parser.add_argument("package", type=Path)
    parser.add_argument("version")
    parser.add_argument("commit")
    args = parser.parse_args()
    try:
        report = inspect_package(args.package, args.version, args.commit)
    except (PackageError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"PACKAGE-FAIL: {error}", file=sys.stderr)
        return 1
    print(report)
    print(f"PACKAGE-OK: {args.version} ({args.commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
