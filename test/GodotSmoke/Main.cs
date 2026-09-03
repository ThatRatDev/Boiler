using System;
using Godot;
using Steamworks;

namespace Boiler.GodotSmoke;

public partial class Main : Node
{
    public override void _Ready()
    {
        try
        {
            SteamClient.Init(480U);
            GD.Print($"GODOT-NATIVE-OK: Steam initialized ({SteamClient.Name}).");
            SteamClient.Shutdown();
            GetTree().Quit(0);
        }
        catch (Exception exception)
        {
            if (exception.Message.StartsWith("SteamApi_Init failed with ", StringComparison.Ordinal))
            {
                GD.Print($"GODOT-NATIVE-OK: native loaded; Steam unavailable ({exception.Message}).");
                GetTree().Quit(0);
                return;
            }

            GD.PrintErr($"GODOT-NATIVE-FAIL: {exception}");
            GetTree().Quit(1);
        }
    }
}
