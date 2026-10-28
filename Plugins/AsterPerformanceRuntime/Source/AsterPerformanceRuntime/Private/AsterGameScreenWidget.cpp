#include "AsterGameScreenWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/EditableText.h"
#include "Components/Image.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/Button.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture2D.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "Styling/CoreStyle.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"

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
    FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), FontSize);
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
    UImage* Room = AddImage(Canvas, TEXT("ArchiveRoom"), Background, FVector2D::ZeroVector, FVector2D(1280.0f, 720.0f));
    Room->SetColorAndOpacity(FLinearColor(.57f, .63f, .64f, 1.0f));
    LampGlow = AddImage(Canvas, TEXT("LampGlow"), nullptr, FVector2D(680, 210), FVector2D(300, 260));
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IoneLampGlow_UI.M_IoneLampGlow_UI")))
    {
        GlowMaterial = UMaterialInstanceDynamic::Create(Mat, this);
        LampGlow->SetBrushFromMaterial(GlowMaterial);
    }
    else LampGlow->SetVisibility(ESlateVisibility::Collapsed);
    BackShadow = AddImage(Canvas, TEXT("BackShadow"), nullptr, FVector2D(40, 40), FVector2D(426, 620));
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IoneBackShadow_UI.M_IoneBackShadow_UI")))
    {
        ShadowMaterial = UMaterialInstanceDynamic::Create(Mat, this);
        BackShadow->SetBrushFromMaterial(ShadowMaterial);
    }
    else BackShadow->SetVisibility(ESlateVisibility::Collapsed);
    AddImage(Canvas, TEXT("ContactShadow"), Shadow, FVector2D(128.0f, 628.0f), FVector2D(320.0f, 70.0f));
    PortraitImage = AddImage(Canvas, TEXT("IoneCharacter"), nullptr, FVector2D(78.0f, 24.0f), FVector2D(426.0f, 639.0f));
    PortraitSlot = Cast<UCanvasPanelSlot>(PortraitImage->Slot);
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IonePortraitLight_UI.M_IonePortraitLight_UI")))
    {
        PortraitLight = UMaterialInstanceDynamic::Create(Mat, this);
        PortraitImage->SetBrushFromMaterial(PortraitLight);
    }
    UImage* DialogueFrame = AddImage(Canvas, TEXT("DialogueFrame"), Frame, FVector2D(488.0f, 500.0f), FVector2D(770.0f, 198.0f));
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IoneDialogue_UI.M_IoneDialogue_UI"))) DialogueFrame->SetBrushFromMaterial(Mat);
    AddText(Canvas, TEXT("ArchiveTitle"), TEXT("The Archive of Forgotten Voices"), FVector2D(520, 30), FVector2D(600, 28), 14, FLinearColor(.87f,.84f,.77f));
    AddText(Canvas, TEXT("ObjectiveLabel"), TEXT("CURRENT OBJECTIVE"), FVector2D(880, 110), FVector2D(330, 24), 14, FLinearColor(.78f,.72f,.62f));
    AddText(Canvas, TEXT("Objective"), TEXT("Find the first public lead to your sister's recording."), FVector2D(880, 143), FVector2D(330, 90), 20, FLinearColor(.87f,.84f,.77f));
    AddText(Canvas, TEXT("Chapter"), TEXT("Chapter I - First Contact"), FVector2D(880, 240), FVector2D(330, 24), 14, FLinearColor(.70f,.72f,.68f));
    SpeakerText = AddText(Canvas, TEXT("Speaker"), TEXT("Ione"), FVector2D(521.0f, 518.0f), FVector2D(530.0f, 30.0f), 22, FLinearColor(0.90f, 0.76f, 0.56f));
    DialogueText = AddText(Canvas, TEXT("Dialogue"), TEXT("You're looking for a voice. We can start with the public index.\nWhat do you remember about her last message?"), FVector2D(523.0f, 555.0f), FVector2D(682.0f, 70.0f), 19, FLinearColor(0.96f, 0.92f, 0.84f));
    ActionCueText = AddText(Canvas, TEXT("ActionCue"), TEXT(""), FVector2D(1050.0f, 518.0f), FVector2D(170.0f, 26.0f), 16, FLinearColor(0.91f, 0.75f, 0.46f));
    InputText = WidgetTree->ConstructWidget<UEditableText>(UEditableText::StaticClass(), TEXT("PlayerInput"));
    InputText->SetHintText(FText::GetEmpty());
    FEditableTextStyle InputStyle = InputText->WidgetStyle;
    InputStyle.SetColorAndOpacity(FSlateColor(FLinearColor(0.96f, 0.92f, 0.84f)));
    InputText->SetWidgetStyle(InputStyle);
    FSlateFontInfo InputFont = InputText->GetFont();
    InputFont.Size = 19;
    InputText->SetFont(InputFont);
    UCanvasPanelSlot* InputSlot = Canvas->AddChildToCanvas(InputText);
    InputSlot->SetPosition(FVector2D(524.0f, 632.0f));
    InputSlot->SetSize(FVector2D(630.0f, 43.0f));
    InputText->OnTextCommitted.AddDynamic(this, &UAsterGameScreenWidget::HandleInputCommitted);
    InputPromptText = AddText(Canvas, TEXT("InputPrompt"), TEXT("Ask Ione anything..."),
        FVector2D(529.0f, 637.0f), FVector2D(530.0f, 32.0f), 17,
        FLinearColor(0.74f, 0.70f, 0.61f));
    InputPromptText->SetVisibility(ESlateVisibility::HitTestInvisible);
    AddText(Canvas, TEXT("InputHint"), TEXT("ENTER"), FVector2D(1165.0f, 641.0f), FVector2D(70.0f, 27.0f), 15,
        FLinearColor(0.74f, 0.70f, 0.61f));
    UButton* MotionButton = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("MotionToggle"));
    UCanvasPanelSlot* MotionSlot = Canvas->AddChildToCanvas(MotionButton);
    MotionSlot->SetPosition(FVector2D(50,680)); MotionSlot->SetSize(FVector2D(230,28));
    MotionButton->SetBackgroundColor(FLinearColor(.04f,.07f,.08f,.75f));
    MotionLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("MotionLabel"));
    MotionLabel->SetText(FText::FromString(TEXT("Reduce motion: Off")));
    FSlateFontInfo MotionFont = MotionLabel->GetFont(); MotionFont.Size = 14; MotionLabel->SetFont(MotionFont);
    MotionButton->AddChild(MotionLabel);
    MotionButton->OnClicked.AddDynamic(this, &UAsterGameScreenWidget::ToggleReducedMotion);
}

void UAsterGameScreenWidget::ToggleReducedMotion()
{
    bReducedMotion = !bReducedMotion;
    if (MotionLabel) MotionLabel->SetText(FText::FromString(bReducedMotion ? TEXT("Reduce motion: On") : TEXT("Reduce motion: Off")));
}

void UAsterGameScreenWidget::UpdatePortraitLayers()
{
    if (!Character) return;
    UTexture2D* Texture = Character->GetPortraitTexture();
    if (PortraitLight) PortraitLight->SetTextureParameterValue(TEXT("Portrait"), Texture);
    else PortraitImage->SetBrushFromTexture(Texture, true);
    if (ShadowMaterial) ShadowMaterial->SetTextureParameterValue(TEXT("Portrait"), Texture);
    if (PortraitLight) PortraitLight->SetScalarParameterValue(TEXT("PoseIndex"), static_cast<int32>(Character->GetPortraitPose()));
}

void UAsterGameScreenWidget::BindCharacter(AAsterNPCActor* InCharacter)
{
    Character = InCharacter;
    if (Character && PortraitImage)
    {
        UpdatePortraitLayers();
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
    if (InputPromptText && InputText)
    {
        InputPromptText->SetVisibility(InputText->GetText().IsEmpty()
            ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    }
    MotionTime += InDeltaTime;
#if !UE_BUILD_SHIPPING
    // Explicit authoring launch option; no debug controls are shown in the game UI.
    if (Character && FParse::Param(FCommandLine::Get(), TEXT("IoneVisualReview")) && MotionTime >= 20.0f)
    {
        const int32 Index = FMath::FloorToInt((MotionTime-20.0f)/4.0f);
        if (Index < 4)
        {
            if (Index != ReviewPoseIndex)
            {
                ReviewPoseIndex = Index;
                Character->SetPortraitPose(static_cast<EAsterPortraitPose>(Index));
                bReviewCapturePending = true;
            }
            if (bReviewCapturePending && FMath::Fmod(MotionTime-20.0f,4.0f) >= 1.5f)
            {
                FScreenshotRequest::RequestScreenshot(FString::Printf(TEXT("IoneReview_%d"),Index),true,true);
                bReviewCapturePending = false;
            }
        }
        else if (ReviewPoseIndex != 4)
        {
            ReviewPoseIndex = 4;
            Character->SetPortraitPose(EAsterPortraitPose::Listening);
        }
    }
#endif
    const float Lamp = bReducedMotion ? 1.0f : 1.0f + .028f * FMath::Sin(MotionTime*.71f) + .012f*FMath::Sin(MotionTime*1.13f);
    if (PortraitLight) PortraitLight->SetScalarParameterValue(TEXT("Lamp"), Lamp);
    if (GlowMaterial) GlowMaterial->SetScalarParameterValue(TEXT("Lamp"), Lamp);
    if (ShadowMaterial) ShadowMaterial->SetScalarParameterValue(TEXT("Lamp"), Lamp);
    if (CueSeconds > 0.0f)
    {
        CueSeconds -= InDeltaTime;
        if (CueSeconds <= 0.0f && ActionCueText) ActionCueText->SetText(FText::GetEmpty());
    }
    if (!Character || !PortraitImage || !PortraitSlot) return;
    const EAsterPortraitPose Pose = Character->GetPortraitPose();
    if (Pose != LastPose)
    {
        LastPose = Pose;
        PosePulse = 1.0f;
        UpdatePortraitLayers();
    }
    PosePulse = FMath::FInterpTo(PosePulse, 0.0f, InDeltaTime, 3.0f);
    const float Bob = bReducedMotion ? 0.0f : FMath::Sin(MotionTime * 1.7f) * .65f;
    const float Accent = Pose == EAsterPortraitPose::Interrupted ? -1.0f : 1.0f;
    const float Pulse = bReducedMotion ? 0.0f : PosePulse;
    PortraitSlot->SetPosition(FVector2D(78.0f + Accent * Pulse * 6.0f, 24.0f + Bob - Pulse * 2.0f));
    PortraitImage->SetRenderTransformAngle(Accent * Pulse * 1.2f);
    if (BackShadow)
    {
        BackShadow->SetRenderTranslation(FVector2D(Accent*Pulse*6.0f, Bob-Pulse*2.0f));
        BackShadow->SetRenderTransformAngle(Accent*Pulse*1.2f);
    }
}

void UAsterGameScreenWidget::HandleInputCommitted(const FText& Text, const ETextCommit::Type CommitMethod)
{
    if (CommitMethod != ETextCommit::OnEnter) return;
    const FString Clean = Text.ToString().TrimStartAndEnd();
    if (Clean.IsEmpty()) return;
    InputText->SetText(FText::GetEmpty());
    SubmitPlayerText(Clean.Left(500));
}

void UAsterGameScreenWidget::SubmitPlayerText(const FString& Text)
{
    if (bRequestInFlight && Character) Character->PlayerInterrupt(Text);
    bRequestInFlight = true;
    ++LatestRequestSerial;
    const int32 SentSerial = LatestRequestSerial;
    SetDialogue(TEXT("Ione"), TEXT("Let me check the archive..."));
    if (ActionCueText) ActionCueText->SetText(FText::GetEmpty());
    if (Character) Character->SetPortraitPose(EAsterPortraitPose::Listening);

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(TEXT("http://127.0.0.1:8765/turn"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json; charset=utf-8"));
    Request->SetTimeout(35.0f);
    TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("text"), Text);
    Body->SetNumberField(TEXT("turn_id"), SentSerial);
    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    FJsonSerializer::Serialize(Body, Writer);
    Request->SetContentAsString(Json);
    Request->OnProcessRequestComplete().BindUObject(this, &UAsterGameScreenWidget::HandleAgentResponse, SentSerial);
    Request->ProcessRequest();
}

void UAsterGameScreenWidget::HandleAgentResponse(TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> /*Request*/,
    TSharedPtr<IHttpResponse, ESPMode::ThreadSafe> Response, const bool bSucceeded, const int32 ResponseSerial)
{
    if (ResponseSerial != LatestRequestSerial) return;
    bRequestInFlight = false;
    if (!bSucceeded || !Response.IsValid() || Response->GetResponseCode() != 200)
    {
        SetDialogue(TEXT("Ione"), TEXT("The archive connection is unavailable. Please start the local archive service and try again."));
        if (Character) Character->SetPortraitPose(EAsterPortraitPose::Warning);
        return;
    }
    TSharedPtr<FJsonObject> Body;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response->GetContentAsString()), Body)
        || !Body.IsValid() || !Body->HasTypedField<EJson::String>(TEXT("dialogue"))
        || !Body->HasTypedField<EJson::String>(TEXT("pose")))
    {
        SetDialogue(TEXT("Ione"), TEXT("I could not read that signal. Please try again."));
        if (Character) Character->SetPortraitPose(EAsterPortraitPose::Warning);
        return;
    }
    SetDialogue(TEXT("Ione"), Body->GetStringField(TEXT("dialogue")));
    const FString Pose = Body->GetStringField(TEXT("pose"));
    if (Character)
    {
        Character->SetPortraitPose(Pose == TEXT("warning") ? EAsterPortraitPose::Warning
            : Pose == TEXT("interrupted") ? EAsterPortraitPose::Interrupted
            : Pose == TEXT("listening") ? EAsterPortraitPose::Listening : EAsterPortraitPose::Speaking);
    }

    const TArray<TSharedPtr<FJsonValue>>* Trace = nullptr;
    if (Body->TryGetArrayField(TEXT("trace"), Trace) && Trace)
    {
        for (const TSharedPtr<FJsonValue>& Value : *Trace)
        {
            const TSharedPtr<FJsonObject> Event = Value.IsValid() ? Value->AsObject() : nullptr;
            if (!Event.IsValid()) continue;
            FString Tool, Target, Result;
            if (!Event->TryGetStringField(TEXT("tool"), Tool)
                || !Event->TryGetStringField(TEXT("target"), Target)
                || !Event->TryGetStringField(TEXT("result"), Result)) continue;
            FString Cue;
            if (Tool == TEXT("inspect_route")) Cue = TEXT("Route checked");
            else if (Tool == TEXT("lookup_record")) Cue = TEXT("Record checked");
            else if (Tool == TEXT("open_archive_door")) Cue = Result == TEXT("opened") ? TEXT("Door open") : TEXT("Permission needed");
            if (!Cue.IsEmpty() && ActionCueText)
            {
                ActionCueText->SetText(FText::FromString(Cue));
                CueSeconds = 4.0f;
            }
            const bool bVerifiedAction = (Tool == TEXT("inspect_route")
                && (Result == TEXT("open") || Result == TEXT("collapsed")))
                || (Tool == TEXT("lookup_record") && Result != TEXT("tool_unavailable")
                    && Result != TEXT("invalid_target"))
                || (Tool == TEXT("open_archive_door") && Result == TEXT("opened"));
            if (Character && bVerifiedAction)
            {
                Character->OnGameActionRequested(FName(*Tool), FName(*Target));
            }
        }
    }
}
