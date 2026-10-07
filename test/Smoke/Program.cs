using System;
using Steamworks;
using ThatRatDev.Steam.Boiler;

SteamNative.Register();

try
{
    SteamClient.Init(480U);
    Console.WriteLine($"NATIVE-OK: Steam initialized ({SteamClient.Name}).");
    SteamClient.Shutdown();
    return 0;
}
catch (Exception e)
{
    if (e.Message.StartsWith("SteamApi_Init failed with ", StringComparison.Ordinal))
    {
        Console.WriteLine($"NATIVE-OK: native loaded; Steam unavailable on CI ({e.Message}).");
        return 0;
    }

    Console.Error.WriteLine($"NATIVE-FAIL: {e}");
    return 1;
}
