#include "AsterPortraitWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Engine/Texture2D.h"

void UAsterPortraitWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();

    if (!WidgetTree)
    {
        WidgetTree = NewObject<UWidgetTree>(this, UWidgetTree::StaticClass(), NAME_None, RF_Transient);
    }

    if (!WidgetTree->RootWidget)
    {
        PortraitLayer = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("IonePortraitLayer"));
        CurrentImage = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("IoneCurrentPose"));
        IncomingImage = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("IoneIncomingPose"));
        PortraitLayer->AddChildToOverlay(CurrentImage);
        PortraitLayer->AddChildToOverlay(IncomingImage);
        IncomingImage->SetRenderOpacity(0.0f);
        WidgetTree->RootWidget = PortraitLayer;
    }
    else
    {
        PortraitLayer = Cast<UOverlay>(WidgetTree->RootWidget);
        CurrentImage = Cast<UImage>(WidgetTree->FindWidget(TEXT("IoneCurrentPose")));
        IncomingImage = Cast<UImage>(WidgetTree->FindWidget(TEXT("IoneIncomingPose")));
    }
}

void UAsterPortraitWidget::SetPortrait(UTexture2D* Texture, const bool bImmediate)
{
    if (!CurrentImage || !IncomingImage || !Texture)
    {
        return;
    }

    if (!CurrentTexture || bImmediate)
    {
        CurrentTexture = Texture;
        IncomingTexture = nullptr;
        CurrentImage->SetBrushFromTexture(Texture, true);
        CurrentImage->SetRenderOpacity(1.0f);
        IncomingImage->SetRenderOpacity(0.0f);
        return;
    }

    if (CurrentTexture == Texture && !IncomingTexture)
    {
        return;
    }

    IncomingTexture = Texture;
    IncomingImage->SetBrushFromTexture(Texture, true);
    IncomingImage->SetRenderOpacity(0.0f);
    CurrentImage->SetRenderOpacity(1.0f);
    TransitionElapsed = 0.0f;
}

void UAsterPortraitWidget::AdvanceTransition(const float DeltaSeconds)
{
    if (!IncomingTexture || !CurrentImage || !IncomingImage)
    {
        return;
    }

    TransitionElapsed += DeltaSeconds;
    const float Alpha = FMath::Clamp(TransitionElapsed / TransitionSeconds, 0.0f, 1.0f);
    CurrentImage->SetRenderOpacity(1.0f - Alpha);
    IncomingImage->SetRenderOpacity(Alpha);
    if (Alpha >= 1.0f)
    {
        CurrentTexture = IncomingTexture;
        IncomingTexture = nullptr;
        CurrentImage->SetBrushFromTexture(CurrentTexture, true);
        CurrentImage->SetRenderOpacity(1.0f);
        IncomingImage->SetRenderOpacity(0.0f);
    }
}
