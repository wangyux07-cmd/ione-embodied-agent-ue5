#include "AsterGameScreenWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/EditableText.h"
#include "Components/Image.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Engine/Texture2D.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

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
    DialogueText = AddText(Canvas, TEXT("Dialogue"), TEXT("信号接通了。你想查哪一份记录？"), FVector2D(523.0f, 555.0f), FVector2D(682.0f, 70.0f), 22, FLinearColor(0.96f, 0.92f, 0.84f));
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
    InputPromptText = AddText(Canvas, TEXT("InputPrompt"), TEXT("点击输入，和伊欧妮说话…"),
        FVector2D(529.0f, 637.0f), FVector2D(530.0f, 32.0f), 17,
        FLinearColor(0.74f, 0.70f, 0.61f));
    InputPromptText->SetVisibility(ESlateVisibility::HitTestInvisible);
    AddText(Canvas, TEXT("InputHint"), TEXT("ENTER"), FVector2D(1165.0f, 641.0f), FVector2D(70.0f, 27.0f), 15,
        FLinearColor(0.74f, 0.70f, 0.61f));
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
    if (InputPromptText && InputText)
    {
        InputPromptText->SetVisibility(InputText->GetText().IsEmpty()
            ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    }
    MotionTime += InDeltaTime;
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
        PortraitImage->SetBrushFromTexture(Character->GetPortraitTexture(), true);
    }
    PosePulse = FMath::FInterpTo(PosePulse, 0.0f, InDeltaTime, 3.0f);
    const float Bob = FMath::Sin(MotionTime * 1.7f) * 2.5f;
    const float Accent = Pose == EAsterPortraitPose::Interrupted ? -1.0f : 1.0f;
    PortraitSlot->SetPosition(FVector2D(78.0f + Accent * PosePulse * 22.0f, 24.0f + Bob - PosePulse * 10.0f));
    PortraitImage->SetRenderTransformAngle(Accent * PosePulse * 4.0f);
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
    SetDialogue(TEXT("伊 欧 妮  ·  I O N E"), TEXT("正在核验档案站的信息…"));
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
        SetDialogue(TEXT("伊 欧 妮  ·  I O N E"), TEXT("这段信号没接通。请确认本地档案站服务正在运行。"));
        if (Character) Character->SetPortraitPose(EAsterPortraitPose::Warning);
        return;
    }
    TSharedPtr<FJsonObject> Body;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response->GetContentAsString()), Body)
        || !Body.IsValid() || !Body->HasTypedField<EJson::String>(TEXT("dialogue"))
        || !Body->HasTypedField<EJson::String>(TEXT("pose")))
    {
        SetDialogue(TEXT("伊 欧 妮  ·  I O N E"), TEXT("收到了一段无法识别的信号。"));
        if (Character) Character->SetPortraitPose(EAsterPortraitPose::Warning);
        return;
    }
    SetDialogue(TEXT("伊 欧 妮  ·  I O N E"), Body->GetStringField(TEXT("dialogue")));
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
            if (Tool == TEXT("inspect_route")) Cue = TEXT("路线已核验");
            else if (Tool == TEXT("lookup_record")) Cue = TEXT("记录已查验");
            else if (Tool == TEXT("open_archive_door")) Cue = Result == TEXT("opened") ? TEXT("门锁已解除") : TEXT("需要授权");
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
