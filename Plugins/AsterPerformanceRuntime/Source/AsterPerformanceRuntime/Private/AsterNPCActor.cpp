#include "AsterNPCActor.h"

#include "AsterSemanticPerformanceComponent.h"
#include "AsterPortraitWidget.h"
#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Components/InputComponent.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "NiagaraComponent.h"
#include "TimerManager.h"
#include "InputCoreTypes.h"

AAsterNPCActor::AAsterNPCActor()
{
    PrimaryActorTick.bCanEverTick = true;

    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
    SetRootComponent(SceneRoot);

    CharacterMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CharacterMesh"));
    CharacterMesh->SetupAttachment(SceneRoot);

    VoiceAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("VoiceAudio"));
    VoiceAudio->SetupAttachment(SceneRoot);
    VoiceAudio->bAutoActivate = false;

    SemanticVfx = CreateDefaultSubobject<UNiagaraComponent>(TEXT("SemanticVfx"));
    SemanticVfx->SetupAttachment(CharacterMesh);
    SemanticVfx->bAutoActivate = false;

    Performance = CreateDefaultSubobject<UAsterSemanticPerformanceComponent>(TEXT("Performance"));

    PortraitWidget = CreateDefaultSubobject<UWidgetComponent>(TEXT("PortraitWidget"));
    PortraitWidget->SetupAttachment(SceneRoot);
    PortraitWidget->SetWidgetClass(UAsterPortraitWidget::StaticClass());
    PortraitWidget->SetWidgetSpace(EWidgetSpace::World);
    PortraitWidget->SetDrawSize(FVector2D(1024.0f, 1536.0f));
    PortraitWidget->SetPivot(FVector2D(0.5f, 1.0f));
    PortraitWidget->SetTwoSided(true);
    PortraitWidget->SetRelativeScale3D(FVector(0.12f, 0.12f, 0.12f));
}

void AAsterNPCActor::BeginPlay()
{
    Super::BeginPlay();
    if (CharacterMesh && CharacterMesh->GetSkeletalMeshAsset())
    {
        VoiceAudio->AttachToComponent(CharacterMesh, FAttachmentTransformRules::KeepRelativeTransform, TEXT("head"));
    }
    PortraitWidget->InitWidget();
    PortraitBaseLocation = PortraitWidget->GetRelativeLocation();
    Performance->OnGestureStarted.AddDynamic(this, &AAsterNPCActor::HandleGestureStarted);
    SetPortraitPose(EAsterPortraitPose::Listening);
    if (bEnablePortraitDebugKeys)
    {
        if (APlayerController* Player = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
        {
            EnableInput(Player);
            if (InputComponent)
            {
                InputComponent->BindKey(EKeys::One, IE_Pressed, this, &AAsterNPCActor::DemoListening);
                InputComponent->BindKey(EKeys::Two, IE_Pressed, this, &AAsterNPCActor::DemoSpeaking);
                InputComponent->BindKey(EKeys::Three, IE_Pressed, this, &AAsterNPCActor::DemoInterrupted);
                InputComponent->BindKey(EKeys::Four, IE_Pressed, this, &AAsterNPCActor::DemoWarning);
            }
        }
    }
}

void AAsterNPCActor::DemoListening() { SetPortraitPose(EAsterPortraitPose::Listening); }
void AAsterNPCActor::DemoSpeaking() { SetPortraitPose(EAsterPortraitPose::Speaking); }
void AAsterNPCActor::DemoInterrupted() { SetPortraitPose(EAsterPortraitPose::Interrupted); }
void AAsterNPCActor::DemoWarning() { SetPortraitPose(EAsterPortraitPose::Warning); }

void AAsterNPCActor::Tick(const float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!PortraitWidget || !PortraitWidget->IsVisible())
    {
        return;
    }

    PortraitMotionTime += DeltaSeconds;
    GesturePulse = FMath::FInterpTo(GesturePulse, 0.0f, DeltaSeconds, 3.5f);
    const float Bob = FMath::Sin(PortraitMotionTime * 1.7f) * IdleBobAmplitudeCm;
    const float Direction = CurrentPortraitPose == EAsterPortraitPose::Interrupted ? -1.0f : 1.0f;
    PortraitWidget->SetRelativeLocation(PortraitBaseLocation + FVector(0.0f, Direction * GesturePulse * GestureDisplacementCm, Bob + GesturePulse * 5.0f));

    if (UAsterPortraitWidget* Widget = Cast<UAsterPortraitWidget>(PortraitWidget->GetUserWidgetObject()))
    {
        Widget->AdvanceTransition(DeltaSeconds);
    }

    if (const APlayerController* Player = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
    {
        if (const APlayerCameraManager* Camera = Player->PlayerCameraManager)
        {
            FRotator Facing = (Camera->GetCameraLocation() - PortraitWidget->GetComponentLocation()).Rotation();
            Facing.Roll += Direction * GesturePulse * GestureTiltDegrees;
            PortraitWidget->SetWorldRotation(Facing);
        }
    }
}

void AAsterNPCActor::SetPortraitPose(const EAsterPortraitPose NewPose)
{
    CurrentPortraitPose = NewPose;
    UTexture2D* Texture = nullptr;
    switch (NewPose)
    {
    case EAsterPortraitPose::Listening: Texture = ListeningPortrait; break;
    case EAsterPortraitPose::Speaking: Texture = SpeakingPortrait; break;
    case EAsterPortraitPose::Interrupted: Texture = InterruptedPortrait; break;
    case EAsterPortraitPose::Warning: Texture = WarningPortrait; break;
    }

    if (UAsterPortraitWidget* Widget = PortraitWidget ? Cast<UAsterPortraitWidget>(PortraitWidget->GetUserWidgetObject()) : nullptr)
    {
        Widget->SetPortrait(Texture, NewPose == EAsterPortraitPose::Interrupted);
    }
    GesturePulse = 1.0f;
}

UTexture2D* AAsterNPCActor::GetPortraitTexture() const
{
    switch (CurrentPortraitPose)
    {
    case EAsterPortraitPose::Speaking: return SpeakingPortrait;
    case EAsterPortraitPose::Interrupted: return InterruptedPortrait;
    case EAsterPortraitPose::Warning: return WarningPortrait;
    default: return ListeningPortrait;
    }
}

void AAsterNPCActor::HandleGestureStarted(FName /*GestureId*/, FName SemanticFunction)
{
    const FString Function = SemanticFunction.ToString().ToLower();
    if (Function.Contains(TEXT("warn")) || Function.Contains(TEXT("refus"))
        || Function.Contains(TEXT("consent")) || Function.Contains(TEXT("boundary")))
    {
        SetPortraitPose(EAsterPortraitPose::Warning);
    }
    else
    {
        SetPortraitPose(EAsterPortraitPose::Speaking);
    }
}

void AAsterNPCActor::ResetPortraitToListening()
{
    SetPortraitPose(EAsterPortraitPose::Listening);
}

void AAsterNPCActor::Perform(const FAsterPerformanceRequest& Request)
{
    if (!Performance)
    {
        return;
    }

    const FAsterPerformancePlan Plan = Performance->BuildPlan(Request, ActiveStrategy);
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(ReturnToListeningTimer);
    }
    SetPortraitPose(EAsterPortraitPose::Speaking);
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
    SetPortraitPose(EAsterPortraitPose::Interrupted);
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(ReturnToListeningTimer);
        World->GetTimerManager().SetTimer(ReturnToListeningTimer, this, &AAsterNPCActor::ResetPortraitToListening, 0.85f, false);
    }
    OnPlayerTookTheFloor(NewPlayerUtterance);
}
