#include "AsterGameScreenWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Image.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Engine/Texture2D.h"

UImage* UAsterGameScreenWidget::AddImage(UCanvasPanel* Canvas, const TCHAR* Name,
    UTexture2D* Texture, const FVector2D& Position, const FVector2D& Size)
{
    UImage* Image = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), FName(Name));
    if (Texture)
    {
        Image->SetBrushFromTexture(Texture, true);
    }
    UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(Image);
    CanvasSlot->SetPosition(Position);
    CanvasSlot->SetSize(Size);
    return Image;
}

UTextBlock* UAsterGameScreenWidget::AddText(UCanvasPanel* Canvas, const TCHAR* Name,
    const FString& Value, const FVector2D& Position, const FVector2D& Size,
    const int32 FontSize, const FLinearColor& Color)
{
    UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), FName(Name));
    Label->SetText(FText::FromString(Value));
    FSlateFontInfo Font = Label->GetFont();
    Font.Size = FontSize;
    Label->SetFont(Font);
    Label->SetColorAndOpacity(FSlateColor(Color));
    Label->SetAutoWrapText(true);
    UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(Label);
    CanvasSlot->SetPosition(Position);
    CanvasSlot->SetSize(Size);
    return Label;
}

void UAsterGameScreenWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    if (!WidgetTree)
    {
        WidgetTree = NewObject<UWidgetTree>(this, UWidgetTree::StaticClass(), NAME_None, RF_Transient);
    }

    UScaleBox* Scale = WidgetTree->ConstructWidget<UScaleBox>(UScaleBox::StaticClass(), TEXT("ScreenScale"));
    Scale->SetStretch(EStretch::ScaleToFit);
    USizeBox* DesignSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("DesignSize"));
    DesignSize->SetWidthOverride(1280.0f);
    DesignSize->SetHeightOverride(720.0f);
    UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("SceneCanvas"));
    WidgetTree->RootWidget = Scale;
    Scale->AddChild(DesignSize);
    DesignSize->AddChild(Canvas);

    UTexture2D* Background = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_ArchiveRoom_Background_v2.Ione_ArchiveRoom_Background_v2"));
    UTexture2D* Shadow = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_ContactShadow.Ione_ContactShadow"));
    UTexture2D* Frame = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_DialogueFrame.Ione_DialogueFrame"));
    AddImage(Canvas, TEXT("ArchiveRoom"), Background, FVector2D::ZeroVector, FVector2D(1280.0f, 720.0f));
    AddImage(Canvas, TEXT("ContactShadow"), Shadow, FVector2D(128.0f, 628.0f), FVector2D(320.0f, 70.0f));
    PortraitImage = AddImage(Canvas, TEXT("IoneCharacter"), nullptr, FVector2D(78.0f, 24.0f), FVector2D(426.0f, 639.0f));
    PortraitSlot = Cast<UCanvasPanelSlot>(PortraitImage->Slot);
    AddImage(Canvas, TEXT("DialogueFrame"), Frame, FVector2D(488.0f, 505.0f), FVector2D(770.0f, 188.0f));
    SpeakerText = AddText(Canvas, TEXT("Speaker"), TEXT("伊 欧 妮  ·  I O N E"), FVector2D(521.0f, 518.0f), FVector2D(530.0f, 30.0f), 22, FLinearColor(0.90f, 0.76f, 0.56f));
    DialogueText = AddText(Canvas, TEXT("Dialogue"), TEXT("信号接通了。你想查哪一份记录？"), FVector2D(523.0f, 560.0f), FVector2D(682.0f, 95.0f), 27, FLinearColor(0.96f, 0.92f, 0.84f));
    AddText(Canvas, TEXT("InputHint"), TEXT("ENTER  开始对话"), FVector2D(1010.0f, 652.0f), FVector2D(205.0f, 27.0f), 16, FLinearColor(0.74f, 0.70f, 0.61f));
}

void UAsterGameScreenWidget::BindCharacter(AAsterNPCActor* InCharacter)
{
    Character = InCharacter;
    if (Character && PortraitImage)
    {
        PortraitImage->SetBrushFromTexture(Character->GetPortraitTexture(), true);
        LastPose = Character->GetPortraitPose();
    }
}

void UAsterGameScreenWidget::SetDialogue(const FString& Speaker, const FString& Line)
{
    if (SpeakerText) SpeakerText->SetText(FText::FromString(Speaker));
    if (DialogueText) DialogueText->SetText(FText::FromString(Line));
}

void UAsterGameScreenWidget::NativeTick(const FGeometry& MyGeometry, const float InDeltaTime)
{
    Super::NativeTick(MyGeometry, InDeltaTime);
    MotionTime += InDeltaTime;
    if (!Character || !PortraitImage || !PortraitSlot) return;
    const EAsterPortraitPose Pose = Character->GetPortraitPose();
    if (Pose != LastPose)
    {
        LastPose = Pose;
        PosePulse = 1.0f;
        PortraitImage->SetBrushFromTexture(Character->GetPortraitTexture(), true);
    }
    PosePulse = FMath::FInterpTo(PosePulse, 0.0f, InDeltaTime, 3.0f);
    const float Bob = FMath::Sin(MotionTime * 1.7f) * 2.5f;
    const float Accent = Pose == EAsterPortraitPose::Interrupted ? -1.0f : 1.0f;
    PortraitSlot->SetPosition(FVector2D(78.0f + Accent * PosePulse * 14.0f, 24.0f + Bob - PosePulse * 7.0f));
    PortraitImage->SetRenderTransformAngle(Accent * PosePulse * 3.0f);
}
