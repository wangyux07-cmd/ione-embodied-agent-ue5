#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TimerManager.h"
#include "AsterPerformanceTypes.h"
#include "AsterNPCActor.generated.h"

class UAudioComponent;
class UNiagaraComponent;
class USceneComponent;
class USkeletalMeshComponent;
class UWidgetComponent;
class UTexture2D;
class UAsterSemanticPerformanceComponent;

UENUM(BlueprintType)
enum class EAsterPortraitPose : uint8
{
    Listening,
    Speaking,
    Interrupted,
    Warning
};

UCLASS(Blueprintable)
class ASTERPERFORMANCERUNTIME_API AAsterNPCActor : public AActor
{
    GENERATED_BODY()

public:
    AAsterNPCActor();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster")
    TObjectPtr<USceneComponent> SceneRoot;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster")
    TObjectPtr<USkeletalMeshComponent> CharacterMesh;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster")
    TObjectPtr<UAudioComponent> VoiceAudio;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster")
    TObjectPtr<UNiagaraComponent> SemanticVfx;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster")
    TObjectPtr<UAsterSemanticPerformanceComponent> Performance;

    /** Camera-facing 2D performance layer. Assign imported PNG textures in a Blueprint subclass. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Aster|Portrait")
    TObjectPtr<UWidgetComponent> PortraitWidget;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait")
    TObjectPtr<UTexture2D> ListeningPortrait;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait")
    TObjectPtr<UTexture2D> SpeakingPortrait;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait")
    TObjectPtr<UTexture2D> InterruptedPortrait;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait")
    TObjectPtr<UTexture2D> WarningPortrait;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait", meta=(ClampMin="0.0"))
    float IdleBobAmplitudeCm = 2.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait", meta=(ClampMin="0.0"))
    float GestureDisplacementCm = 10.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Portrait", meta=(ClampMin="0.0"))
    float GestureTiltDegrees = 5.0f;

    /** Test map only: keys 1-4 preview the authored poses; keep disabled in a user build. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Debug")
    bool bEnablePortraitDebugKeys = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Runtime")
    EAsterPerformanceStrategy ActiveStrategy = EAsterPerformanceStrategy::Semantic;

    UFUNCTION(BlueprintCallable, Category="Aster|Runtime")
    void Perform(const FAsterPerformanceRequest& Request);

    UFUNCTION(BlueprintCallable, Category="Aster|Runtime")
    void PlayerInterrupt(const FString& NewPlayerUtterance);

    UFUNCTION(BlueprintCallable, Category="Aster|Portrait")
    void SetPortraitPose(EAsterPortraitPose NewPose);

    UFUNCTION(BlueprintPure, Category="Aster|Portrait")
    EAsterPortraitPose GetPortraitPose() const { return CurrentPortraitPose; }

    UFUNCTION(BlueprintPure, Category="Aster|Portrait")
    UTexture2D* GetPortraitTexture() const;

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnDialogueStarted(const FString& Dialogue);

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnPlayerTookTheFloor(const FString& NewPlayerUtterance);

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnGameActionRequested(FName ActionId, FName WorldTarget);

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

private:
    UFUNCTION()
    void HandleGestureStarted(FName GestureId, FName SemanticFunction);

    UFUNCTION()
    void ResetPortraitToListening();

    void DemoListening();
    void DemoSpeaking();
    void DemoInterrupted();
    void DemoWarning();

    FTimerHandle ReturnToListeningTimer;
    FVector PortraitBaseLocation = FVector::ZeroVector;
    float PortraitMotionTime = 0.0f;
    float GesturePulse = 0.0f;
    EAsterPortraitPose CurrentPortraitPose = EAsterPortraitPose::Listening;
};
