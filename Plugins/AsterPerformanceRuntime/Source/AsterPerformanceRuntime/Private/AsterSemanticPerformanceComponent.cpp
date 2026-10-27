#include "AsterSemanticPerformanceComponent.h"

#include "Animation/AnimInstance.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "TimerManager.h"

UAsterSemanticPerformanceComponent::UAsterSemanticPerformanceComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

const FAsterGestureDefinition* UAsterSemanticPerformanceComponent::FindBestGesture(
    const FAsterSemanticAnchor& Anchor,
    const FAsterPerformanceRequest& Request) const
{
    if (!GestureLibrary)
    {
        return nullptr;
    }

    const FAsterGestureDefinition* Best = nullptr;
    float BestScore = -1.0f;
    for (const FAsterGestureDefinition& Candidate : GestureLibrary->Gestures)
    {
        if (!Candidate.SemanticFunctions.Contains(Anchor.Function)
            || Request.ForbiddenGestures.Contains(Candidate.GestureId)
            || Candidate.BlockedStateTags.HasAny(Request.CurrentStateTags)
            || !Request.CharacterTags.HasAll(Candidate.RequiredCharacterTags))
        {
            continue;
        }

        const float Score = Anchor.Confidence * 2.0f - FMath::Abs(Candidate.Intensity - 0.5f);
        if (Score > BestScore)
        {
            BestScore = Score;
            Best = &Candidate;
        }
    }
    return Best;
}

FAsterPerformancePlan UAsterSemanticPerformanceComponent::BuildPlan(
    const FAsterPerformanceRequest& Request,
    const EAsterPerformanceStrategy Strategy) const
{
    FAsterPerformancePlan Plan;
    Plan.PlanId = FGuid::NewGuid();
    Plan.Dialogue = Request.Dialogue;
    Plan.Strategy = Strategy;

    if (!GestureLibrary || GestureLibrary->Gestures.IsEmpty())
    {
        return Plan;
    }

    if (Strategy == EAsterPerformanceStrategy::FlatTag)
    {
        if (!Request.SemanticAnchors.IsEmpty())
        {
            if (const FAsterGestureDefinition* Match = FindBestGesture(Request.SemanticAnchors[0], Request))
            {
                Plan.Gestures.Add({ Match->GestureId, Request.SemanticAnchors[0].Function, 0.2f, Match->DurationSeconds, Match->InterruptPolicy });
            }
        }
        return Plan;
    }

    if (Strategy == EAsterPerformanceStrategy::Rhythm)
    {
        const int32 BeatCount = FMath::Clamp(Request.Dialogue.Len() / 42, 1, 4);
        for (int32 Index = 0; Index < BeatCount; ++Index)
        {
            Plan.Gestures.Add({ TEXT("beat_small"), TEXT("rhythm"), 0.55f + Index * 1.15f, 0.7f, EAsterInterruptPolicy::SoftCancel });
        }
        return Plan;
    }

    for (const FAsterSemanticAnchor& Anchor : Request.SemanticAnchors)
    {
        if (Anchor.Confidence < 0.55f)
        {
            Plan.Gestures.Add({ TEXT("beat_small"), TEXT("rhythm_fallback"), Anchor.TriggerSeconds, 0.7f, EAsterInterruptPolicy::SoftCancel });
            continue;
        }

        if (const FAsterGestureDefinition* Match = FindBestGesture(Anchor, Request))
        {
            Plan.Gestures.Add({ Match->GestureId, Anchor.Function, Anchor.TriggerSeconds, Match->DurationSeconds, Match->InterruptPolicy });
        }
    }

    Plan.Gestures.Sort([](const FAsterScheduledGesture& A, const FAsterScheduledGesture& B)
    {
        return A.StartSeconds < B.StartSeconds;
    });
    return Plan;
}

void UAsterSemanticPerformanceComponent::PlayPlan(
    const FAsterPerformancePlan& Plan,
    UAnimInstance* AnimInstance,
    UNiagaraComponent* SemanticVfx)
{
    ResetExecutor();
    ActivePlan = Plan;
    SetExecutorState(EAsterExecutorState::Speaking);
    OnPlanReady.Broadcast(ActivePlan);

    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    for (int32 Index = 0; Index < ActivePlan.Gestures.Num(); ++Index)
    {
        FTimerHandle Handle;
        FTimerDelegate Delegate = FTimerDelegate::CreateUObject(
            this,
            &UAsterSemanticPerformanceComponent::StartScheduledGesture,
            Index,
            AnimInstance,
            SemanticVfx);
        World->GetTimerManager().SetTimer(Handle, Delegate, ActivePlan.Gestures[Index].StartSeconds, false);
        ScheduledTimers.Add(Handle);
    }
}

void UAsterSemanticPerformanceComponent::StartScheduledGesture(
    const int32 GestureIndex,
    UAnimInstance* AnimInstance,
    UNiagaraComponent* SemanticVfx)
{
    if (!ActivePlan.Gestures.IsValidIndex(GestureIndex) || ExecutorState != EAsterExecutorState::Speaking)
    {
        return;
    }

    ActiveGestureIndex = GestureIndex;
    const FAsterScheduledGesture& Scheduled = ActivePlan.Gestures[GestureIndex];
    if (GestureLibrary && AnimInstance)
    {
        const FAsterGestureDefinition* Definition = GestureLibrary->Gestures.FindByPredicate(
            [&Scheduled](const FAsterGestureDefinition& Item) { return Item.GestureId == Scheduled.GestureId; });
        if (Definition && Definition->Montage)
        {
            AnimInstance->Montage_Play(Definition->Montage);
        }
    }

    if (SemanticVfx)
    {
        SemanticVfx->SetVariableFloat(TEXT("User.SemanticIntensity"), 1.0f);
        SemanticVfx->SetVariableFloat(TEXT("User.InterruptStrength"), 0.0f);
        SemanticVfx->Activate(true);
    }
    OnGestureStarted.Broadcast(Scheduled.GestureId, Scheduled.SemanticFunction);
}

void UAsterSemanticPerformanceComponent::Interrupt(UAnimInstance* AnimInstance, UNiagaraComponent* SemanticVfx)
{
    LastInterruptRequestSeconds = FPlatformTime::Seconds();
    int32 CancelledCount = 0;
    if (UWorld* World = GetWorld())
    {
        for (FTimerHandle& Timer : ScheduledTimers)
        {
            if (World->GetTimerManager().IsTimerActive(Timer))
            {
                ++CancelledCount;
                World->GetTimerManager().ClearTimer(Timer);
            }
        }
    }
    ScheduledTimers.Reset();

    SetExecutorState(EAsterExecutorState::Recovering);
    const EAsterInterruptPolicy Policy = ActivePlan.Gestures.IsValidIndex(ActiveGestureIndex)
        ? ActivePlan.Gestures[ActiveGestureIndex].InterruptPolicy
        : EAsterInterruptPolicy::Immediate;

    if (AnimInstance && Policy != EAsterInterruptPolicy::FinishPhrase)
    {
        AnimInstance->Montage_Stop(Policy == EAsterInterruptPolicy::Immediate ? 0.05f : SoftCancelBlendOutSeconds);
    }
    if (SemanticVfx)
    {
        SemanticVfx->SetVariableFloat(TEXT("User.InterruptStrength"), 1.0f);
        SemanticVfx->DeactivateImmediate();
    }

    const float LatencyMs = static_cast<float>((FPlatformTime::Seconds() - LastInterruptRequestSeconds) * 1000.0);
    OnInterrupted.Broadcast(LatencyMs, CancelledCount);
    SetExecutorState(EAsterExecutorState::Listening);
}

void UAsterSemanticPerformanceComponent::ResetExecutor()
{
    if (UWorld* World = GetWorld())
    {
        for (FTimerHandle& Timer : ScheduledTimers)
        {
            World->GetTimerManager().ClearTimer(Timer);
        }
    }
    ScheduledTimers.Reset();
    ActiveGestureIndex = INDEX_NONE;
    ActivePlan = FAsterPerformancePlan();
    SetExecutorState(EAsterExecutorState::Idle);
}

void UAsterSemanticPerformanceComponent::SetExecutorState(const EAsterExecutorState NewState)
{
    if (ExecutorState != NewState)
    {
        ExecutorState = NewState;
        OnStateChanged.Broadcast(ExecutorState);
    }
}
