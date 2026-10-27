using UnrealBuildTool;
using System.Collections.Generic;

public class AsterPerformanceLabTarget : TargetRules
{
    public AsterPerformanceLabTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ExtraModuleNames.Add("AsterPerformanceLab");
    }
}
