#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import inspect_export


class ExportInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def touch(self, relative: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def test_linux_accepts_exact_platform_pair(self) -> None:
        self.touch("data/Facepunch.Steamworks.Posix.dll")
        self.touch("data/libsteam_api.so")
        report = inspect_export.inspect_inventory("linux", self.root, check_architecture=False)
        self.assertIn("Facepunch.Steamworks.Posix.dll", report)
        self.assertIn("libsteam_api.so", report)

    def test_linux_rejects_non_elf_native_when_checking_architecture(self) -> None:
        self.touch("data/Facepunch.Steamworks.Posix.dll")
        self.touch("data/libsteam_api.so")
        with self.assertRaisesRegex(inspect_export.InventoryError, "ELF"):
            inspect_export.inspect_inventory("linux", self.root)

    def test_windows_rejects_posix_wrapper(self) -> None:
        self.touch("data/Facepunch.Steamworks.Posix.dll")
        self.touch("data/steam_api64.dll")
        with self.assertRaisesRegex(inspect_export.InventoryError, "wrong-platform"):
            inspect_export.inspect_inventory("windows", self.root, check_architecture=False)

    def test_macos_accepts_one_pair_per_architecture(self) -> None:
        for architecture in ("x86_64", "arm64"):
            directory = f"Smoke.app/Contents/Resources/data_Smoke_macos_{architecture}"
            self.touch(f"{directory}/Facepunch.Steamworks.Posix.dll")
            self.touch(f"{directory}/libsteam_api.dylib")
        report = inspect_export.inspect_inventory("macos", self.root, check_architecture=False)
        self.assertEqual(4, len(report.splitlines()))

    def test_macos_rejects_foreign_native(self) -> None:
        self.touch("Smoke.app/Contents/Resources/Facepunch.Steamworks.Posix.dll")
        self.touch("Smoke.app/Contents/Resources/libsteam_api.dylib")
        self.touch("Smoke.app/Contents/Resources/libsteam_api.so")
        with self.assertRaisesRegex(inspect_export.InventoryError, "wrong-platform"):
            inspect_export.inspect_inventory("macos", self.root, check_architecture=False)

    def test_duplicate_expected_native_is_rejected(self) -> None:
        self.touch("one/Facepunch.Steamworks.Posix.dll")
        self.touch("one/libsteam_api.so")
        self.touch("two/libsteam_api.so")
        with self.assertRaisesRegex(inspect_export.InventoryError, "exactly one"):
            inspect_export.inspect_inventory("linux", self.root, check_architecture=False)

    def test_missing_managed_wrapper_is_rejected(self) -> None:
        self.touch("libsteam_api.so")
        with self.assertRaisesRegex(inspect_export.InventoryError, "exactly one"):
            inspect_export.inspect_inventory("linux", self.root, check_architecture=False)


if __name__ == "__main__":
    unittest.main()
