#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

STEAM_FILES = {
    "Facepunch.Steamworks.Win64.dll",
    "Facepunch.Steamworks.Posix.dll",
    "steam_api64.dll",
    "libsteam_api.so",
    "libsteam_api.dylib",
}
EXPECTED = {
    "windows": {"Facepunch.Steamworks.Win64.dll", "steam_api64.dll"},
    "linux": {"Facepunch.Steamworks.Posix.dll", "libsteam_api.so"},
    "macos": {"Facepunch.Steamworks.Posix.dll", "libsteam_api.dylib"},
}


class InventoryError(RuntimeError):
    pass


def require_elf_x64(path: Path) -> None:
    header = path.read_bytes()[:20]
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise InventoryError(f"{path} is not an ELF binary")
    if header[4] != 2:
        raise InventoryError(f"{path} is not a 64-bit ELF binary")
    byte_order = "little" if header[5] == 1 else "big" if header[5] == 2 else ""
    if not byte_order or int.from_bytes(header[18:20], byte_order) != 0x3E:
        raise InventoryError(f"{path} is not an x86_64 ELF binary")


def require_pe_x64(path: Path) -> None:
    with path.open("rb") as binary:
        header = binary.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            raise InventoryError(f"{path} is not a PE binary")
        binary.seek(int.from_bytes(header[60:64], "little"))
        pe_header = binary.read(6)
    if len(pe_header) != 6 or pe_header[:4] != b"PE\0\0":
        raise InventoryError(f"{path} has an invalid PE header")
    if int.from_bytes(pe_header[4:6], "little") != 0x8664:
        raise InventoryError(f"{path} is not an x64 PE binary")


def relative_paths(root: Path, name: str) -> list[Path]:
    return sorted(path.relative_to(root) for path in root.rglob(name) if path.is_file())


def require_universal(path: Path) -> None:
    try:
        result = subprocess.run(
            ["lipo", "-archs", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise InventoryError(f"could not inspect macOS architectures for {path}: {error}") from error
    architectures = set(result.stdout.split())
    missing = {"x86_64", "arm64"} - architectures
    if missing:
        raise InventoryError(f"{path} is not universal; missing {', '.join(sorted(missing))}")


def inspect_inventory(target: str, root: Path, *, check_architecture: bool = True) -> str:
    if target not in EXPECTED:
        raise InventoryError(f"unsupported target: {target}")
    if not root.is_dir():
        raise InventoryError(f"export directory does not exist: {root}")

    found = {name: relative_paths(root, name) for name in STEAM_FILES}
    expected = EXPECTED[target]
    wrong = [(name, path) for name, paths in found.items() if name not in expected for path in paths]
    if wrong:
        details = ", ".join(str(path) for _, path in wrong)
        raise InventoryError(f"found wrong-platform Steam binaries: {details}")

    if target == "macos":
        expected_directories: set[Path] | None = None
        for name in sorted(expected):
            paths = found[name]
            if len(paths) != 2:
                raise InventoryError(f"expected one {name} per macOS architecture, found {len(paths)}")
            directories = {path.parent for path in paths}
            architecture_directories = {
                architecture
                for architecture in ("x86_64", "arm64")
                if any(directory.name.endswith(f"_macos_{architecture}") for directory in directories)
            }
            if architecture_directories != {"x86_64", "arm64"}:
                raise InventoryError(f"{name} is not present in both macOS architecture directories")
            if expected_directories is None:
                expected_directories = directories
            elif directories != expected_directories:
                raise InventoryError("macOS managed and native files are not colocated")
    else:
        for name in sorted(expected):
            if len(found[name]) != 1:
                raise InventoryError(f"expected exactly one {name}, found {len(found[name])}")

    if check_architecture:
        if target == "linux":
            require_elf_x64(root / found["libsteam_api.so"][0])
            executables = list(root.glob("*.x86_64"))
            if len(executables) != 1:
                raise InventoryError(f"expected one Linux x64 executable, found {len(executables)}")
            require_elf_x64(executables[0])
        elif target == "windows":
            require_pe_x64(root / found["steam_api64.dll"][0])
            executables = list(root.glob("*.exe"))
            if len(executables) != 1:
                raise InventoryError(f"expected one Windows x64 executable, found {len(executables)}")
            require_pe_x64(executables[0])
        else:
            for relative in found["libsteam_api.dylib"]:
                require_universal(root / relative)
            executables = [path for path in root.glob("*.app/Contents/MacOS/*") if path.is_file()]
            if len(executables) != 1:
                raise InventoryError(f"expected one macOS app executable, found {len(executables)}")
            require_universal(executables[0])

    inventory = [str(path) for name in sorted(expected) for path in found[name]]
    return "\n".join(inventory)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Steam binaries in a Godot export.")
    parser.add_argument("target", choices=sorted(EXPECTED))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_inventory(args.target, args.directory)
    except InventoryError as error:
        print(f"EXPORT-INVENTORY-FAIL: {error}", file=sys.stderr)
        return 1
    print(report)
    print(f"EXPORT-INVENTORY-OK: {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
