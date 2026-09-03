#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from test import inspect_package


class PackageInspectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "Boiler.nupkg"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def nuspec() -> bytes:
        return b"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TheDevRatt.Steam.Boiler</id>
    <version>0.3.2</version>
    <projectUrl>https://github.com/TheDevRatt/Boiler</projectUrl>
    <license type="expression">MIT</license>
    <repository type="git" url="https://github.com/TheDevRatt/Boiler.git" commit="abc123" />
  </metadata>
</package>
"""

    def write_package(
        self,
        *,
        missing: str | None = None,
        malformed_nuspec: bool = False,
        duplicate: str | None = None,
    ) -> None:
        files = {name: b"fixture" for name in inspect_package.REQUIRED_FILES if name != missing}
        files["THIRD-PARTY-NOTICES.md"] = (
            b"Copyright (c) 2016 Facepunch Studios LTD\nSteamworks SDK Access Agreement\n"
        )
        files["Boiler.nuspec"] = b"<broken" if malformed_nuspec else self.nuspec()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.package, "w") as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
                if duplicate is not None:
                    archive.writestr(duplicate, b"conflicting second copy")

    def test_accepts_exact_package(self) -> None:
        self.write_package()
        report = inspect_package.inspect_package(self.package, "0.3.2", "abc123")
        self.assertIn("THIRD-PARTY-NOTICES.md", report)

    def test_rejects_missing_required_asset(self) -> None:
        missing = "steam/native/win-x64/steam_api64.dll"
        self.write_package(missing=missing)
        with self.assertRaisesRegex(inspect_package.PackageError, "missing package files"):
            inspect_package.inspect_package(self.package, "0.3.2", "abc123")

    def test_rejects_malformed_nuspec(self) -> None:
        self.write_package(malformed_nuspec=True)
        with self.assertRaises(ET.ParseError):
            inspect_package.inspect_package(self.package, "0.3.2", "abc123")

    def test_rejects_duplicate_archive_path(self) -> None:
        duplicate = "steam/native/win-x64/steam_api64.dll"
        self.write_package(duplicate=duplicate)
        with self.assertRaisesRegex(inspect_package.PackageError, "duplicate package path"):
            inspect_package.inspect_package(self.package, "0.3.2", "abc123")


if __name__ == "__main__":
    unittest.main()
