# Boiler technical design

**Status:** Implemented
**Package:** `ThatRatDev.Steam.Boiler`
**Runtime:** .NET 8 and Godot 4 C#

## Scope

Boiler is a native-loading package for Facepunch.Steamworks. It is not a Steam API wrapper, multiplayer transport, or project template.

A Steam integration has two platform-sensitive layers:

| Layer | Files |
| --- | --- |
| Managed wrapper | `Facepunch.Steamworks.Win64.dll` or `Facepunch.Steamworks.Posix.dll` |
| Native library | `steam_api64.dll`, `libsteam_api.so`, or `libsteam_api.dylib` |

The managed wrapper calls versioned Steam interface accessors through P/Invoke. A wrapper and native library from different SDK generations can therefore load but fail on a missing entry point.

## Why Godot needs a loader

NuGet normally places native dependencies under `runtimes/<rid>/native/`. Godot editor builds commonly have no runtime identifier, so those files are not copied beside the game assemblies. Godot's host load context also does not probe that NuGet layout like a normal `dotnet` application. Boiler therefore performs both jobs explicitly: MSBuild places the target native in the output, then a resolver loads it from the running application's directory.

## Package behavior

The package keeps both managed variants and all three desktop native libraries under `steam/`. Its imported MSBuild files:

1. Select the Windows or Posix managed reference from the target runtime identifier, falling back to the build host when no identifier is set.
2. Copy only the target platform's native library to the build output.
3. Compile a module initializer into the consumer assembly.

The initializer calls `SteamNative.Register()`. The resolver attaches to the selected Facepunch assembly and loads the native library from the application base directory or executable directory.

## Upstream policy

Version 0.4.0 pins the official Facepunch.Steamworks 2.5.2 release. Its two managed assemblies and three native libraries are kept as one matched set. Upgrades replace and validate all five files together from an official release archive. Unreleased upstream binaries are not substituted into a package that claims a stable release.

Facepunch.Steamworks 2.5.2 has a known SteamInput lifecycle defect. It does not explicitly initialize or shut down Steam Input and does not clear cached controller handles. This can produce zero detected controllers or stale handles after Steam shutdown and reinitialization. The upstream fix has not yet been published in a stable release.

## Validation

CI is configured to perform these checks:

- Pack the source version and inspect package metadata and assets.
- Run a console native-load smoke test on Windows, Linux, and macOS.
- Run a Godot 4.7.2 .NET headless smoke scene on each host without requiring Steam credentials.
- Export Windows x64, Linux x64, and macOS universal builds on their native runners.
- Reject exported builds with a missing, duplicate, or foreign Steam managed/native binary.
- Verify both x64 and arm64 slices in the exported macOS executable and Steam dylib.
- Compare the Posix wrapper's required interface accessors with the bundled dylib exports.

A scheduled workflow compares the pinned Facepunch version with the latest stable GitHub release. It creates or updates one open issue only when the upstream stable version is newer.
