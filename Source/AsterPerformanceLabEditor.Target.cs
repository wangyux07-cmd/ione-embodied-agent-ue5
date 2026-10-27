using UnrealBuildTool;
using System.Collections.Generic;

public class AsterPerformanceLabEditorTarget : TargetRules
{
    public AsterPerformanceLabEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ExtraModuleNames.Add("AsterPerformanceLab");
    }
}
