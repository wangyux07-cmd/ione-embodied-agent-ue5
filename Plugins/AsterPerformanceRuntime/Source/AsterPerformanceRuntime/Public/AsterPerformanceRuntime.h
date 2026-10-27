#pragma once

#include "Modules/ModuleManager.h"

class FAsterPerformanceRuntimeModule final : public IModuleInterface
{
public:
    virtual void StartupModule() override;
};
