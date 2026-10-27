#include "AsterNPCActor.h"

#include "AsterSemanticPerformanceComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "NiagaraComponent.h"

AAsterNPCActor::AAsterNPCActor()
{
    PrimaryActorTick.bCanEverTick = false;

    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
    SetRootComponent(SceneRoot);

    CharacterMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CharacterMesh"));
    CharacterMesh->SetupAttachment(SceneRoot);

    VoiceAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("VoiceAudio"));
    VoiceAudio->SetupAttachment(CharacterMesh, TEXT("head"));
    VoiceAudio->bAutoActivate = false;

    SemanticVfx = CreateDefaultSubobject<UNiagaraComponent>(TEXT("SemanticVfx"));
    SemanticVfx->SetupAttachment(CharacterMesh);
    SemanticVfx->bAutoActivate = false;

    Performance = CreateDefaultSubobject<UAsterSemanticPerformanceComponent>(TEXT("Performance"));
}

void AAsterNPCActor::Perform(const FAsterPerformanceRequest& Request)
{
    if (!Performance)
    {
        return;
    }

    const FAsterPerformancePlan Plan = Performance->BuildPlan(Request, ActiveStrategy);
    Performance->PlayPlan(Plan, CharacterMesh ? CharacterMesh->GetAnimInstance() : nullptr, SemanticVfx);
    OnDialogueStarted(Request.Dialogue);
}

void AAsterNPCActor::PlayerInterrupt(const FString& NewPlayerUtterance)
{
    if (VoiceAudio)
    {
        VoiceAudio->FadeOut(0.08f, 0.0f);
    }
    if (Performance)
    {
        Performance->Interrupt(CharacterMesh ? CharacterMesh->GetAnimInstance() : nullptr, SemanticVfx);
    }
    OnPlayerTookTheFloor(NewPlayerUtterance);
}
