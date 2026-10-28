#include "AsterGameMode.h"

#include "AsterGameScreenWidget.h"
#include "AsterNPCActor.h"
#include "Components/WidgetComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

void AAsterGameMode::BeginPlay()
{
    Super::BeginPlay();
    APlayerController* Player = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
    if (!Player) return;
    UAsterGameScreenWidget* Screen = CreateWidget<UAsterGameScreenWidget>(Player, UAsterGameScreenWidget::StaticClass());
    if (!Screen) return;
    Screen->AddToViewport();
    for (TActorIterator<AAsterNPCActor> It(GetWorld()); It; ++It)
    {
        AAsterNPCActor* Ione = *It;
        if (Ione && Ione->PortraitWidget)
        {
            Ione->PortraitWidget->SetVisibility(false);
            Screen->BindCharacter(Ione);
            break;
        }
    }
}
