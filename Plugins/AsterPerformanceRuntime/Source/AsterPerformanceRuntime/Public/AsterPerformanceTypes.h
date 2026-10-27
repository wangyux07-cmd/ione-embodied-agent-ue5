#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimMontage.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "NiagaraSystem.h"
#include "AsterPerformanceTypes.generated.h"

UENUM(BlueprintType)
enum class EAsterPerformanceStrategy : uint8
{
    FlatTag,
    Rhythm,
    Semantic
};

UENUM(BlueprintType)
enum class EAsterInterruptPolicy : uint8
{
    Immediate,
    SoftCancel,
    FinishPhrase
};

UENUM(BlueprintType)
enum class EAsterExecutorState : uint8
{
    Idle,
    Planning,
    Speaking,
    Recovering,
    Listening
};

USTRUCT(BlueprintType)
struct FAsterSemanticAnchor
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName Function = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.0"))
    float TriggerSeconds = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.0", ClampMax="1.0"))
    float Confidence = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName WorldTarget = NAME_None;
};

USTRUCT(BlueprintType)
struct FAsterGestureDefinition
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FName GestureId = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    TArray<FName> SemanticFunctions;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FGameplayTagContainer RequiredCharacterTags;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FGameplayTagContainer BlockedStateTags;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    TObjectPtr<UAnimMontage> Montage = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    TObjectPtr<UNiagaraSystem> AccentEffect = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.05"))
    float DurationSeconds = 1.2f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.0", ClampMax="1.0"))
    float Intensity = 0.5f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    EAsterInterruptPolicy InterruptPolicy = EAsterInterruptPolicy::SoftCancel;
};

USTRUCT(BlueprintType)
struct FAsterScheduledGesture
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    FName GestureId = NAME_None;

    UPROPERTY(BlueprintReadOnly)
    FName SemanticFunction = NAME_None;

    UPROPERTY(BlueprintReadOnly)
    float StartSeconds = 0.0f;

    UPROPERTY(BlueprintReadOnly)
    float DurationSeconds = 0.0f;

    UPROPERTY(BlueprintReadOnly)
    EAsterInterruptPolicy InterruptPolicy = EAsterInterruptPolicy::SoftCancel;
};

USTRUCT(BlueprintType)
struct FAsterPerformanceRequest
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString Dialogue;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    TArray<FAsterSemanticAnchor> SemanticAnchors;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FGameplayTagContainer CharacterTags;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FGameplayTagContainer CurrentStateTags;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    TArray<FName> ForbiddenGestures;
};

USTRUCT(BlueprintType)
struct FAsterPerformancePlan
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    FGuid PlanId;

    UPROPERTY(BlueprintReadOnly)
    FString Dialogue;

    UPROPERTY(BlueprintReadOnly)
    EAsterPerformanceStrategy Strategy = EAsterPerformanceStrategy::Semantic;

    UPROPERTY(BlueprintReadOnly)
    TArray<FAsterScheduledGesture> Gestures;
};

UCLASS(BlueprintType)
class ASTERPERFORMANCERUNTIME_API UAsterGestureLibrary : public UDataAsset
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    TArray<FAsterGestureDefinition> Gestures;
};
