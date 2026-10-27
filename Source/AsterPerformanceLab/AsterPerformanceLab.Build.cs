using UnrealBuildTool;

public class AsterPerformanceLab : ModuleRules
{
    public AsterPerformanceLab(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "InputCore", "AsterPerformanceRuntime" });
    }
}
