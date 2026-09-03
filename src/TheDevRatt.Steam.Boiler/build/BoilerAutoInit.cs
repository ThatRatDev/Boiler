// This file is compiled into the consumer by TheDevRatt.Steam.Boiler.props.
// CA2255 is suppressed because automatic resolver registration is intentional.
#pragma warning disable CA2255

namespace TheDevRatt.Steam.Boiler.Generated
{
    internal static class BoilerAutoInit
    {
        [System.Runtime.CompilerServices.ModuleInitializer]
        internal static void Initialize() => TheDevRatt.Steam.Boiler.SteamNative.Register();
    }
}

#pragma warning restore CA2255
