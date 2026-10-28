#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "AsterNPCActor.h"
#include "AsterGameScreenWidget.generated.h"

class UCanvasPanel;
class UCanvasPanelSlot;
class UImage;
class UTextBlock;

/** Player-facing 2.5D scene. All copy stays in editable UMG controls. */
UCLASS()
class ASTERPERFORMANCERUNTIME_API UAsterGameScreenWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    void BindCharacter(AAsterNPCActor* InCharacter);
    void SetDialogue(const FString& Speaker, const FString& Line);

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
    UImage* AddImage(UCanvasPanel* Canvas, const TCHAR* Name, UTexture2D* Texture,
        const FVector2D& Position, const FVector2D& Size);
    UTextBlock* AddText(UCanvasPanel* Canvas, const TCHAR* Name, const FString& Value,
        const FVector2D& Position, const FVector2D& Size, int32 FontSize, const FLinearColor& Color);

    UPROPERTY(Transient)
    TObjectPtr<AAsterNPCActor> Character;
    UPROPERTY(Transient)
    TObjectPtr<UImage> PortraitImage;
    UPROPERTY(Transient)
    TObjectPtr<UCanvasPanelSlot> PortraitSlot;
    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> SpeakerText;
    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> DialogueText;

    EAsterPortraitPose LastPose = EAsterPortraitPose::Listening;
    float MotionTime = 0.0f;
    float PosePulse = 0.0f;
};
