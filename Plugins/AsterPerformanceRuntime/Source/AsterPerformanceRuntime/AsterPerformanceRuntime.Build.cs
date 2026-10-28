using UnrealBuildTool;

public class AsterPerformanceRuntime : ModuleRules
{
    public AsterPerformanceRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core", "CoreUObject", "Engine", "GameplayTags", "HTTP", "InputCore", "Json", "JsonUtilities", "Niagara", "Projects", "RenderCore", "UMG", "Slate", "SlateCore"
        });
    }
}
