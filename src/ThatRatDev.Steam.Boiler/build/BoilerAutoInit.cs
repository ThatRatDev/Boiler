// This file is compiled into the consumer by ThatRatDev.Steam.Boiler.props.
// CA2255 is suppressed because automatic resolver registration is intentional.
#pragma warning disable CA2255

namespace ThatRatDev.Steam.Boiler.Generated
{
    internal static class BoilerAutoInit
    {
        [System.Runtime.CompilerServices.ModuleInitializer]
        internal static void Initialize() => ThatRatDev.Steam.Boiler.SteamNative.Register();
    }
}

#pragma warning restore CA2255
