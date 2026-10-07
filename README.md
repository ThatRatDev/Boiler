# Steam Boiler

Boiler is a .NET 8 package that makes Facepunch.Steamworks native loading work in Godot C# projects. It selects the platform-specific managed wrapper, copies the matching Steam native library, and installs a `DllImport` resolver through a module initializer.

## Install

```sh
dotnet add package ThatRatDev.Steam.Boiler
```

Use the normal Facepunch API:

```csharp
using Steamworks;

SteamClient.Init(480); // Spacewar, Valve's public test app ID
GD.Print($"Steam: {SteamClient.Name}");
```

The resolver is registered before game code runs. `SteamNative.Register()` is also public and idempotent if explicit registration is useful.

### Migrating from `TheDevRatt.Steam.Boiler`

Versions 0.3.2 and earlier were published as `TheDevRatt.Steam.Boiler`. From 0.4.0 the package ID and namespace are `ThatRatDev.Steam.Boiler`; the bundled binaries and behavior are unchanged.

```sh
dotnet remove package TheDevRatt.Steam.Boiler
dotnet add package ThatRatDev.Steam.Boiler
```

If you call `SteamNative.Register()` explicitly, update `using TheDevRatt.Steam.Boiler;` to `using ThatRatDev.Steam.Boiler;`.

On Windows, `SteamClient.Init(appId)` is enough to run outside Steam. On macOS and Linux it is not: Facepunch passes the App ID through `Environment.SetEnvironmentVariable`, which .NET does not expose to native code there, so Steam fails with `No appID found`. During development, put a `steam_appid.txt` containing just the App ID in the directory the game is launched from (the project folder for `godot --path`). Games launched by the Steam client don't need it, and it should not ship. Shipping on Steam requires Steamworks partner access and compliance with Valve's terms.

## Peer-to-peer example

A minimal host/client echo over Steam's relay network, using Facepunch's `SteamNetworkingSockets` API directly. Nobody needs to forward ports: Steam relays the traffic, and peers address each other by SteamID.

Save this as `SteamP2P.cs` and attach it to a node in your main scene:

```csharp
using System;
using System.Runtime.InteropServices;
using Godot;
using Steamworks;
using Steamworks.Data;

// Host: run with no arguments. Client: run with `-- --connect=<host SteamID64>`.
public partial class SteamP2P : Node
{
    private EchoHost _host;
    private EchoClient _client;
    private ulong _hostId; // 0 = act as host
    private bool _started;

    public override void _Ready()
    {
        // Run callbacks from _Process so they fire on Godot's main thread.
        SteamClient.Init(480, asyncCallbacks: false);
        SteamNetworkingUtils.InitRelayNetworkAccess();

        string connect = Array.Find(OS.GetCmdlineUserArgs(), arg => arg.StartsWith("--connect="));
        if (connect != null)
        {
            _hostId = ulong.Parse(connect.Substring("--connect=".Length));
        }
    }

    public override void _Process(double delta)
    {
        SteamClient.RunCallbacks();

        // Relay sockets fail until Steam's relay network is ready.
        if (!_started && SteamNetworkingUtils.Status == SteamNetworkingAvailability.Current)
        {
            _started = true;
            if (_hostId == 0)
            {
                _host = SteamNetworkingSockets.CreateRelaySocket<EchoHost>();
                GD.Print($"Hosting as {SteamClient.SteamId}");
            }
            else
            {
                _client = SteamNetworkingSockets.ConnectRelay<EchoClient>(_hostId);
                GD.Print($"Connecting to {_hostId}");
            }
        }

        _host?.Receive();
        _client?.Receive();
    }

    public override void _ExitTree()
    {
        _client?.Close();
        _host?.Close();
        SteamClient.Shutdown();
    }
}

public class EchoHost : SocketManager
{
    public override void OnConnected(Connection connection, ConnectionInfo info)
    {
        base.OnConnected(connection, info); // Required: registers the connection for Receive().
        GD.Print($"{info.Identity.SteamId} connected");
    }

    public override void OnMessage(Connection connection, NetIdentity identity, IntPtr data, int size, long messageNum, long recvTime, int channel)
    {
        string text = Marshal.PtrToStringUTF8(data, size);
        GD.Print($"{identity.SteamId}: {text}");
        connection.SendMessage($"echo: {text}");
    }
}

public class EchoClient : ConnectionManager
{
    public override void OnConnected(ConnectionInfo info)
    {
        base.OnConnected(info);
        Connection.SendMessage($"hello from {SteamClient.Name}");
    }

    public override void OnMessage(IntPtr data, int size, long messageNum, long recvTime, int channel)
    {
        GD.Print(Marshal.PtrToStringUTF8(data, size));
    }
}
```

To try it, run each side on a separate machine, logged into a different Steam account. Steam only lets an account connect to itself inside a single process, so two copies on one account fail with `Invalid Connection`. Spacewar (480) is free to every account. On macOS and Linux, add a `steam_appid.txt` containing `480` first (see above).

1. On the host, run the project normally. After a few seconds, once the relay network is ready, it prints `Hosting as <SteamID64>`.
2. On the client, pass that ID after `--`, for example `godot --path . -- --connect=7656119...` or `MyGame.exe -- --connect=7656119...`.

The client sends a greeting and the host echoes it back. Overrides of `SocketManager.OnConnected` must call `base.OnConnected`: it registers the connection with the poll group that `Receive()` reads, so without it the host accepts connections but never receives their messages. `SendMessage(string)` allocates on every call; send `byte[]` or a pointer in real game traffic.

This sends raw messages and does not plug into Godot's high-level multiplayer API (`MultiplayerPeer`, RPCs, `MultiplayerSynchronizer`).

## Bundled release

Boiler 0.4.0 contains the managed and native files from the official [Facepunch.Steamworks 2.5.2 release](https://github.com/Facepunch/Facepunch.Steamworks/releases/tag/2.5.2).

| Target | Managed wrapper | Native library |
| --- | --- | --- |
| Windows x64 | `Facepunch.Steamworks.Win64.dll` | `steam_api64.dll` |
| Linux x64 | `Facepunch.Steamworks.Posix.dll` | `libsteam_api.so` |
| macOS x64 and arm64 | `Facepunch.Steamworks.Posix.dll` | `libsteam_api.dylib` (universal) |

Managed wrappers and native libraries are updated together from one official Facepunch release. Boiler does not substitute binaries built from unreleased upstream commits.

> **SteamInput limitation:** Facepunch.Steamworks 2.5.2 does not explicitly initialize or shut down Steam Input and does not clear its cached controller handles. It can report zero controllers and retain stale handles after Steam shutdown and reinitialization. Upstream has a fix on `master`, but it is not part of an official release yet.

## Compatibility checks

The CI matrix is configured for Godot 4.7.2 with .NET 8. It runs the package in a real headless Godot project on Windows, Linux, and macOS without Steam credentials. Each runner also exports its native desktop target and checks the exported file inventory. The macOS check verifies x64 and arm64 slices with `lipo`.

The console smoke test remains as a direct native-load check. Accessor parity is checked between the managed wrapper and bundled native library.

macOS distribution signing and notarization remain the consuming application's responsibility.

## Release versioning

The project file is the package-version authority. A published GitHub release must use the matching `vX.Y.Z` tag; a manual publish uses the project value. The publish workflow refuses a mismatched tag, a commit not reachable from `main`, or a commit without a successful CI run.

## License

Boiler is MIT licensed. See [LICENSE](LICENSE). Facepunch and Valve attribution and redistribution terms are preserved in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
