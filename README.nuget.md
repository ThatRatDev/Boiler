# Boiler

Boiler provides cross-platform Facepunch.Steamworks native loading for Godot C# on .NET 8. It selects the correct managed wrapper, copies the matching Steam native library, and registers the resolver automatically.

## Install

```sh
dotnet add package ThatRatDev.Steam.Boiler
```

Previously published as `TheDevRatt.Steam.Boiler` (0.3.2 and earlier). Replace that reference with this package; if you call `SteamNative.Register()` explicitly, update the namespace to `ThatRatDev.Steam.Boiler`.

## Use

```csharp
using Steamworks;

SteamClient.Init(480); // Spacewar, Valve's public test app ID
GD.Print($"Steam: {SteamClient.Name}");
```

Boiler 0.4.0 bundles the official Facepunch.Steamworks 2.5.2 managed and native files for Windows x64, Linux x64, and macOS x64/arm64.

> **SteamInput limitation:** Facepunch.Steamworks 2.5.2 can report zero controllers and retain stale controller handles after Steam shutdown and reinitialization. The explicit Steam Input initialization, shutdown, and cache-clearing fix is currently only on upstream `master`, not in an official release. Boiler stays on matched official release files.

Pass the App ID directly to `SteamClient.Init(appId)`; Facepunch sets the process environment for local runs. Shipping requires Steamworks partner access and is subject to Valve's terms.

Boiler and Facepunch.Steamworks are MIT licensed. The package includes the required Facepunch notice and identifies the Valve redistributable terms in `THIRD-PARTY-NOTICES.md`.
