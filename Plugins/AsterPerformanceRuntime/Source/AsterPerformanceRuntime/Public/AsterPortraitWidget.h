#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AsterPortraitWidget.generated.h"

class UImage;
class UOverlay;
class UTexture2D;

/** Native, asset-free widget shell for Ione's authored full-body 2D poses. */
UCLASS()
class ASTERPERFORMANCERUNTIME_API UAsterPortraitWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Aster|Portrait")
    void SetPortrait(UTexture2D* Texture, bool bImmediate = false);

    void AdvanceTransition(float DeltaSeconds);

protected:
    virtual void NativeOnInitialized() override;

private:
    UPROPERTY(Transient)
    TObjectPtr<UOverlay> PortraitLayer;

    UPROPERTY(Transient)
    TObjectPtr<UImage> CurrentImage;

    UPROPERTY(Transient)
    TObjectPtr<UImage> IncomingImage;

    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> CurrentTexture;

    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> IncomingTexture;

    float TransitionElapsed = 0.0f;
    static constexpr float TransitionSeconds = 0.18f;
};
