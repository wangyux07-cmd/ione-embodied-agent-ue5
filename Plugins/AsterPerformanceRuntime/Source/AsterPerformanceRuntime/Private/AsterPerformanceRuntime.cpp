#include "AsterPerformanceRuntime.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "ShaderCore.h"

void FAsterPerformanceRuntimeModule::StartupModule()
{
    const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("AsterPerformanceRuntime"));
    if (Plugin.IsValid())
    {
        AddShaderSourceDirectoryMapping(
            TEXT("/Plugin/AsterPerformance"),
            FPaths::Combine(Plugin->GetBaseDir(), TEXT("Shaders")));
    }
}

IMPLEMENT_MODULE(FAsterPerformanceRuntimeModule, AsterPerformanceRuntime)
