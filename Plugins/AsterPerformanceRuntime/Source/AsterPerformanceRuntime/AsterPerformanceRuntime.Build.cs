using UnrealBuildTool;

public class AsterPerformanceRuntime : ModuleRules
{
    public AsterPerformanceRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core", "CoreUObject", "Engine", "GameplayTags", "Json", "JsonUtilities", "Niagara", "Projects", "RenderCore", "UMG", "Slate", "SlateCore"
        });
    }
}
