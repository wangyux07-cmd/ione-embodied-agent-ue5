#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/EditableText.h"
#include "AsterNPCActor.h"
#include "AsterGameScreenWidget.generated.h"

class UCanvasPanel;
class UCanvasPanelSlot;
class UImage;
class UTextBlock;
class UEditableText;
class IHttpRequest;
class IHttpResponse;
class UMaterialInstanceDynamic;
class FJsonObject;

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
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;

    UFUNCTION()
    void HandleInputCommitted(const FText& Text, ETextCommit::Type CommitMethod);
    UFUNCTION()
    void ToggleJournal();
    UFUNCTION() void ShowStory();
    UFUNCTION() void ShowObjectives();
    UFUNCTION() void ShowClues();
    UFUNCTION() void ShowMemories();
    UFUNCTION() void ShowIone();

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
    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> ActionCueText;
    UPROPERTY(Transient)
    TObjectPtr<UEditableText> InputText;
    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> InputPromptText;
    UPROPERTY(Transient)
    TObjectPtr<UImage> BackShadow;
    UPROPERTY(Transient)
    TObjectPtr<UImage> LampGlow;
    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> PortraitLight;
    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> ShadowMaterial;
    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> GlowMaterial;
    UPROPERTY(Transient)
    TObjectPtr<UCanvasPanel> JournalPanel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JournalHeading;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JournalBody;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> JournalNote;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ObjectiveText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ChapterText;
    UPROPERTY(Transient) TObjectPtr<UImage> JournalUnderline;
    UPROPERTY(Transient) TArray<TObjectPtr<UWidget>> DialogueWidgets;
    void SetJournalPage(int32 Page);
    void InitializeSession();
    void ApplyQuestState(const TSharedPtr<FJsonObject>& Body);
    FString SessionId;
    FString CurrentObjective;
    FString VerifiedClues;
    FString SharedMemories;
    FString RelationshipStage;
    int32 ActiveJournalPage = 1;
    bool bSessionReady = false;
    bool bSessionLoading = false;
    int32 RuntimeReviewStep = 0;
    float RuntimeReviewReadyTime = 0.f;
    bool bReducedMotion = false;
    int32 ReviewPoseIndex = -1;
    bool bReviewCapturePending = false;
    void UpdatePortraitLayers();

    void SubmitPlayerText(const FString& Text);
    void HandleAgentResponse(TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Request,
        TSharedPtr<IHttpResponse, ESPMode::ThreadSafe> Response, bool bSucceeded, int32 ResponseSerial);

    EAsterPortraitPose LastPose = EAsterPortraitPose::Listening;
    float MotionTime = 0.0f;
    float PosePulse = 0.0f;
    float CueSeconds = 0.0f;
    int32 LatestRequestSerial = 0;
    bool bRequestInFlight = false;
};
