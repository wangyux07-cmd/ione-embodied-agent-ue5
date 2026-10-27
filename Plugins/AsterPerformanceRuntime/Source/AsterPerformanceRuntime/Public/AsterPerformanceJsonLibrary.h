#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "AsterPerformanceTypes.h"
#include "AsterPerformanceJsonLibrary.generated.h"

UCLASS()
class ASTERPERFORMANCERUNTIME_API UAsterPerformanceJsonLibrary final : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Aster|Protocol")
    static bool ParsePerformanceRequest(const FString& Json, FAsterPerformanceRequest& OutRequest, FString& OutError);
};
