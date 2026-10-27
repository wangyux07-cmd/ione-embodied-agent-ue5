#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AsterPerformanceTypes.h"
#include "AsterSemanticPerformanceComponent.generated.h"

class UAnimInstance;
class UNiagaraComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAsterPlanReady, const FAsterPerformancePlan&, Plan);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FAsterGestureEvent, FName, GestureId, FName, SemanticFunction);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FAsterInterrupted, float, CancellationLatencyMs, int32, CancelledGestureCount);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAsterStateChanged, EAsterExecutorState, State);

UCLASS(ClassGroup=(Aster), meta=(BlueprintSpawnableComponent))
class ASTERPERFORMANCERUNTIME_API UAsterSemanticPerformanceComponent final : public UActorComponent
{
    GENERATED_BODY()

public:
    UAsterSemanticPerformanceComponent();

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Aster|Authoring")
    TObjectPtr<UAsterGestureLibrary> GestureLibrary;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Aster|Execution", meta=(ClampMin="0.01", ClampMax="1.0"))
    float SoftCancelBlendOutSeconds = 0.18f;

    UPROPERTY(BlueprintAssignable, Category="Aster|Events")
    FAsterPlanReady OnPlanReady;

    UPROPERTY(BlueprintAssignable, Category="Aster|Events")
    FAsterGestureEvent OnGestureStarted;

    UPROPERTY(BlueprintAssignable, Category="Aster|Events")
    FAsterInterrupted OnInterrupted;

    UPROPERTY(BlueprintAssignable, Category="Aster|Events")
    FAsterStateChanged OnStateChanged;

    UFUNCTION(BlueprintCallable, Category="Aster|Planning")
    FAsterPerformancePlan BuildPlan(const FAsterPerformanceRequest& Request, EAsterPerformanceStrategy Strategy) const;

    UFUNCTION(BlueprintCallable, Category="Aster|Execution")
    void PlayPlan(const FAsterPerformancePlan& Plan, UAnimInstance* AnimInstance, UNiagaraComponent* SemanticVfx);

    UFUNCTION(BlueprintCallable, Category="Aster|Execution")
    void Interrupt(UAnimInstance* AnimInstance, UNiagaraComponent* SemanticVfx);

    UFUNCTION(BlueprintCallable, Category="Aster|Execution")
    void ResetExecutor();

    UFUNCTION(BlueprintPure, Category="Aster|Execution")
    EAsterExecutorState GetExecutorState() const { return ExecutorState; }

private:
    const FAsterGestureDefinition* FindBestGesture(const FAsterSemanticAnchor& Anchor, const FAsterPerformanceRequest& Request) const;
    void StartScheduledGesture(int32 GestureIndex, UAnimInstance* AnimInstance, UNiagaraComponent* SemanticVfx);
    void SetExecutorState(EAsterExecutorState NewState);

    UPROPERTY(Transient)
    FAsterPerformancePlan ActivePlan;

    UPROPERTY(Transient)
    EAsterExecutorState ExecutorState = EAsterExecutorState::Idle;

    UPROPERTY(Transient)
    int32 ActiveGestureIndex = INDEX_NONE;

    TArray<FTimerHandle> ScheduledTimers;
    double LastInterruptRequestSeconds = 0.0;
};
