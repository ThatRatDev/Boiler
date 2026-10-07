#!/usr/bin/env python3
from __future__ import annotations

import configparser
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "ThatRatDev.Steam.Boiler" / "ThatRatDev.Steam.Boiler.csproj"
GODOT = ROOT / "test" / "GodotSmoke"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def xml_text(root: ET.Element, name: str) -> str:
    element = root.find(f".//{name}")
    return "" if element is None or element.text is None else element.text.strip()


def validate_package() -> None:
    root = ET.parse(PACKAGE).getroot()
    require(xml_text(root, "PackageId") == "ThatRatDev.Steam.Boiler", "PackageId must be ThatRatDev.Steam.Boiler")
    require(xml_text(root, "Authors") == "ThatRatDev", "package author must be ThatRatDev")
    require(xml_text(root, "Version") == "0.4.0", "package version must be 0.4.0")
    require(xml_text(root, "PackageProjectUrl") == "https://github.com/ThatRatDev/Boiler", "PackageProjectUrl is missing")
    require(xml_text(root, "RepositoryUrl") == "https://github.com/ThatRatDev/Boiler.git", "RepositoryUrl is missing")
    require(xml_text(root, "RepositoryType") == "git", "RepositoryType must be git")
    require(xml_text(root, "RepositoryCommit") == "$(SourceRevisionId)", "RepositoryCommit must use SourceRevisionId")
    require(xml_text(root, "PackageLicenseExpression") == "MIT", "MIT package license metadata changed")
    require(xml_text(root, "FacepunchVersion") == "2.5.2", "pinned Facepunch version must be machine-readable")


def validate_local_package_source(config_path: Path) -> None:
    root = ET.parse(config_path).getroot()
    mapping = root.find("./packageSourceMapping/packageSource[@key='boiler-local']/package[@pattern='ThatRatDev.Steam.Boiler']")
    require(mapping is not None, f"{config_path.relative_to(ROOT)} must map Boiler exclusively to the local CI feed")


def validate_godot_project() -> None:
    required = [
        GODOT / "Boiler.GodotSmoke.csproj",
        GODOT / "Boiler.GodotSmoke.sln",
        GODOT / "Main.cs",
        GODOT / "Main.cs.uid",
        GODOT / "Main.tscn",
        GODOT / "project.godot",
        GODOT / "export_presets.cfg",
        ROOT / "test" / "inspect_export.py",
        ROOT / "test" / "inspect_package.py",
        ROOT / "test" / "test_inspect_package.py",
        ROOT / ".github" / "workflows" / "upstream-release.yml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    require(not missing, "missing maintenance files: " + ", ".join(missing))
    validate_local_package_source(ROOT / "test" / "Smoke" / "nuget.config")
    validate_local_package_source(GODOT / "nuget.config")

    csproj = ET.parse(GODOT / "Boiler.GodotSmoke.csproj").getroot()
    require(csproj.attrib.get("Sdk") == "Godot.NET.Sdk/4.7.2", "smoke project must pin Godot.NET.Sdk 4.7.2")
    package = csproj.find(".//PackageReference[@Include='ThatRatDev.Steam.Boiler']")
    require(package is not None and package.attrib.get("Version") == "0.4.0", "smoke project must consume Boiler 0.4.0")

    solution = (GODOT / "Boiler.GodotSmoke.sln").read_text(encoding="utf-8")
    require("ExportDebug|Any CPU = ExportDebug|Any CPU" in solution, "solution is missing ExportDebug configuration")
    require("ExportRelease|Any CPU = ExportRelease|Any CPU" in solution, "solution is missing ExportRelease configuration")
    require("ExportRelease|Any CPU.ActiveCfg = ExportRelease|Any CPU" in solution, "solution maps ExportRelease incorrectly")

    project = configparser.ConfigParser(interpolation=None, strict=False)
    project_text = (GODOT / "project.godot").read_text(encoding="utf-8")
    project.read_string("[root]\n" + project_text)
    main_scene = project.get("application", "run/main_scene", fallback="").strip('"')
    assembly_name = project.get("dotnet", "project/assembly_name", fallback="").strip('"')
    require(main_scene == "res://Main.tscn", "Godot smoke main scene is not configured")
    require(assembly_name == "Boiler.GodotSmoke", "Godot assembly name is not configured")
    etc2_astc = project.get("rendering", "textures/vram_compression/import_etc2_astc", fallback="")
    require(etc2_astc == "true", "macOS universal export requires ETC2/ASTC import support")

    source = (GODOT / "Main.cs").read_text(encoding="utf-8")
    require("SteamClient.Init" in source, "Godot smoke must call through Facepunch to the native library")
    require("GODOT-NATIVE-OK" in source and "GODOT-NATIVE-FAIL" in source, "Godot smoke must report an unambiguous result")
    require("SteamNative.Register" not in source, "Godot smoke must rely on Boiler's injected module initializer")

    presets = (GODOT / "export_presets.cfg").read_text(encoding="utf-8")
    for platform in ("Windows Desktop", "Linux", "macOS"):
        require(f'platform="{platform}"' in presets, f"missing {platform} export preset")
    require('binary_format/architecture="universal"' in presets, "macOS export must be universal")


def validate_workflows_and_docs() -> None:
    workflow_directory = ROOT / ".github" / "workflows"
    workflow_text = {
        path.name: path.read_text(encoding="utf-8")
        for path in workflow_directory.glob("*.yml")
    }
    action_ref = re.compile(r"^\s*-\s+uses:\s+([^\s#]+)", re.MULTILINE)
    pinned_action = re.compile(r"[^@\s]+@[0-9a-f]{40}")
    for name, text in workflow_text.items():
        for reference in action_ref.findall(text):
            if not reference.startswith("./"):
                require(pinned_action.fullmatch(reference) is not None, f"{name} contains an unpinned GitHub Action reference: {reference}")

    ci = workflow_text["ci.yml"]
    publish = workflow_text["publish.yml"]
    require("RELEASE_TAG: ${{ github.event.release.tag_name }}" in publish, "release tag must enter Bash through the environment")
    require('version="${{ github.event.release.tag_name }}"' not in publish, "release tag is interpolated into Bash source")
    require("test/inspect_package.py" in publish, "publish workflow must inspect the exact package before upload")
    require("NUGET_API_KEY: ${{ steps.login.outputs.NUGET_API_KEY }}" in publish, "NuGet token must enter the shell through an environment variable")
    require("--api-key \"$NUGET_API_KEY\"" in publish, "NuGet token must be quoted at the shell boundary")
    require("actions: read" in publish, "publish workflow must be able to verify CI for its source commit")
    require("git merge-base --is-ancestor" in publish, "publish workflow must require a commit reachable from main")
    require("actions/workflows/ci.yml/runs" in publish, "publish workflow must require a successful CI run for its source commit")
    require('"$version" != "$project_version"' in publish, "publish version must equal the project version")
    require("chickensoft-games/setup-godot@" in ci, "CI must install the Godot .NET editor")
    require("unittest discover -s test" in ci, "CI must run all inspector behavior tests")
    require("version: 4.7.2" in ci and "use-dotnet: true" in ci, "CI must pin the Godot 4.7.2 .NET editor")
    require("include-templates: true" in ci, "CI must install matching .NET export templates")
    require("inspect_export.py" in ci, "CI must inspect actual Godot exports")
    require("NUGET_PACKAGES: ${{ github.workspace }}/.nuget/packages" in ci, "CI smoke jobs must use an isolated package cache")
    require("test/GodotSmoke" in ci, "CI must run the Godot smoke project")

    for smoke_path in (ROOT / "test" / "Smoke" / "Program.cs", GODOT / "Main.cs"):
        smoke = smoke_path.read_text(encoding="utf-8")
        require('StartsWith("SteamApi_Init failed with "' in smoke, f"{smoke_path.relative_to(ROOT)} must only tolerate Facepunch initialization failures")
        require("NATIVE-FAIL" in smoke, f"{smoke_path.relative_to(ROOT)} must fail closed on unexpected exceptions")

    monitor = (ROOT / ".github" / "workflows" / "upstream-release.yml").read_text(encoding="utf-8")
    require("releases/latest" in monitor, "upstream monitor must query the latest release")
    require("issues: write" in monitor and "contents: read" in monitor, "upstream monitor permissions are incomplete")
    require("FacepunchVersion" in monitor, "upstream monitor must read the package pin")
    require('gh issue view "$issue"' in monitor, "upstream monitor must leave an unchanged issue untouched")

    docs = (ROOT / "README.md").read_text(encoding="utf-8") + (ROOT / "README.nuget.md").read_text(encoding="utf-8")
    require("Facepunch.Steamworks 2.5.2" in docs, "documentation must identify the bundled Facepunch release")
    require("zero controllers" in docs and "stale" in docs, "documentation must state the SteamInput limitation")
    require("publish to NuGet.org" not in docs, "stale NuGet publishing TODO remains")


def main() -> int:
    try:
        validate_package()
        validate_godot_project()
        validate_workflows_and_docs()
    except (AssertionError, configparser.Error, ET.ParseError) as error:
        print(f"MAINTENANCE-CONTRACT-FAIL: {error}", file=sys.stderr)
        return 1
    print("MAINTENANCE-CONTRACT-OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
