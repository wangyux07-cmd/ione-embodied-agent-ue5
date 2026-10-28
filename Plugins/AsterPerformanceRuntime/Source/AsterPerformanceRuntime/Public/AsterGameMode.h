#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "AsterGameMode.generated.h"

UCLASS()
class ASTERPERFORMANCERUNTIME_API AAsterGameMode : public AGameModeBase
{
    GENERATED_BODY()

protected:
    virtual void BeginPlay() override;
};
