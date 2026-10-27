#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AsterPerformanceTypes.h"
#include "AsterNPCActor.generated.h"

class UAudioComponent;
class UNiagaraComponent;
class USceneComponent;
class USkeletalMeshComponent;
class UAsterSemanticPerformanceComponent;

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

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Runtime")
    EAsterPerformanceStrategy ActiveStrategy = EAsterPerformanceStrategy::Semantic;

    UFUNCTION(BlueprintCallable, Category="Aster|Runtime")
    void Perform(const FAsterPerformanceRequest& Request);

    UFUNCTION(BlueprintCallable, Category="Aster|Runtime")
    void PlayerInterrupt(const FString& NewPlayerUtterance);

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnDialogueStarted(const FString& Dialogue);

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnPlayerTookTheFloor(const FString& NewPlayerUtterance);

    UFUNCTION(BlueprintImplementableEvent, Category="Aster|Events")
    void OnGameActionRequested(FName ActionId, FName WorldTarget);
};
