using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

namespace ThatRatDev.Steam.Boiler;

/// <summary>
/// Resolves Facepunch.Steamworks native imports to the platform library copied
/// by Boiler's MSBuild targets. A generated module initializer calls
/// <see cref="Register"/> before consumer code runs.
/// </summary>
public static class SteamNative
{
    private static bool _registered;

    /// <summary>Registers the native resolver. Repeated calls have no effect.</summary>
    public static void Register()
    {
        if (_registered)
        {
            return;
        }

        _registered = true;

        // Facepunch uses separate Windows and Posix assemblies with different imports.
        string assemblyName = OperatingSystem.IsWindows()
            ? "Facepunch.Steamworks.Win64"
            : "Facepunch.Steamworks.Posix";

        Assembly facepunch;
        try
        {
            facepunch = Assembly.Load(assemblyName);
        }
        catch (Exception e)
        {
            Console.WriteLine($"[SteamNative] Could not load {assemblyName}: {e.Message}");
            return;
        }

        // Runs from a module initializer, so an exception here would abort the consumer.
        try
        {
            NativeLibrary.SetDllImportResolver(facepunch, Resolve);
        }
        catch (InvalidOperationException e)
        {
            Console.WriteLine($"[SteamNative] Another resolver is already registered for {assemblyName}: {e.Message}");
            return;
        }

        Console.WriteLine($"[SteamNative] Native resolver registered for {assemblyName}.");
    }

    private static IntPtr Resolve(string libraryName, Assembly assembly, DllImportSearchPath? searchPath)
    {
        if (libraryName.IndexOf("steam_api", StringComparison.OrdinalIgnoreCase) < 0)
        {
            return IntPtr.Zero;
        }

        foreach (string path in Candidates())
        {
            if (File.Exists(path) && NativeLibrary.TryLoad(path, out IntPtr handle))
            {
                return handle;
            }
        }

        return IntPtr.Zero;
    }

    private static string NativeFileName()
    {
        if (OperatingSystem.IsWindows())
        {
            return "steam_api64.dll";
        }

        if (OperatingSystem.IsMacOS())
        {
            return "libsteam_api.dylib";
        }

        return "libsteam_api.so";
    }

    private static IEnumerable<string> Candidates()
    {
        string file = NativeFileName();

        yield return Path.Combine(AppContext.BaseDirectory, file);

        // Export layouts can separate the executable from the managed assembly directory.
        string? exeDir = Path.GetDirectoryName(Environment.ProcessPath);
        if (!string.IsNullOrEmpty(exeDir))
        {
            yield return Path.Combine(exeDir, file);
        }
    }
}
