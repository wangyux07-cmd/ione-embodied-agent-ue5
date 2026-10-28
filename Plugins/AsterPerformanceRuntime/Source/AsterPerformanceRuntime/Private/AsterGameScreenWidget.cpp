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
#include "Misc/Paths.h"
#include "InputCoreTypes.h"

namespace IoneStyle
{
    FLinearColor Color(const uint8 R, const uint8 G, const uint8 B, float A=1.f)
    { FLinearColor C=FLinearColor::FromSRGBColor(FColor(R,G,B)); C.A=A; return C; }
    FSlateFontInfo Font(const int32 Pixels, const bool Serif=false)
    {
        const FString File=FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("WINDIR")),TEXT("Fonts"),Serif?TEXT("georgia.ttf"):TEXT("segoeui.ttf"));
        const int32 Points=FMath::RoundToInt(Pixels*.75f);
        return FPaths::FileExists(File) ? FSlateFontInfo(File,Points) : FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),Points);
    }
    void Button(UButton* B,const FLinearColor& Color)
    {
        FSlateBrush Brush;Brush.DrawAs=ESlateBrushDrawType::Image;Brush.TintColor=Color;
        FButtonStyle Style;Style.SetNormal(Brush);Style.SetHovered(Brush);Style.SetPressed(Brush);Style.SetDisabled(Brush);B->SetStyle(Style);
    }
}

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
    const FString Role(Name);
    FSlateFontInfo Font = IoneStyle::Font(FontSize,true);
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

    UTexture2D* Background = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_ArchiveRoom_Background_Selected.Ione_ArchiveRoom_Background_Selected"));
    if(!Background) Background=LoadObject<UTexture2D>(nullptr,TEXT("/Game/UI/Ione_ArchiveRoom_Background_v2.Ione_ArchiveRoom_Background_v2"));
    UTexture2D* Shadow = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_ContactShadow.Ione_ContactShadow"));
    UTexture2D* Frame = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Ione_DialogueFrame.Ione_DialogueFrame"));
    UImage* Room = AddImage(Canvas, TEXT("ArchiveRoom"), Background, FVector2D::ZeroVector, FVector2D(1280.0f, 720.0f));
    Room->SetColorAndOpacity(FLinearColor::White);
    LampGlow = AddImage(Canvas, TEXT("LampGlow"), nullptr, FVector2D(680, 210), FVector2D(300, 260));
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IoneLampGlow_UI.M_IoneLampGlow_UI")))
    {
        GlowMaterial = UMaterialInstanceDynamic::Create(Mat, this);
        LampGlow->SetBrushFromMaterial(GlowMaterial);
    }
    else LampGlow->SetVisibility(ESlateVisibility::Collapsed);
    LampGlow->SetVisibility(ESlateVisibility::Collapsed);
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
    // Freeze the selected painted colors; further relighting is deferred by user.
    UImage* DialogueFrame = AddImage(Canvas, TEXT("DialogueFrame"), Frame, FVector2D(499,449), FVector2D(730,235));
    if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/UI/Materials/M_IoneDialogue_UI.M_IoneDialogue_UI"))) DialogueFrame->SetBrushFromMaterial(Mat);
    const FLinearColor Paper=IoneStyle::Color(223,214,196), Muted=IoneStyle::Color(182,183,170);
    UImage* ObjectiveRule=AddImage(Canvas,TEXT("ObjectiveRule"),nullptr,FVector2D(858,115),FVector2D(2,128)); ObjectiveRule->SetColorAndOpacity(IoneStyle::Color(168,130,89));
    AddText(Canvas, TEXT("ObjectiveLabel"), TEXT("CURRENT OBJECTIVE"), FVector2D(880, 123), FVector2D(330, 22), 13, Paper);
    ObjectiveText=AddText(Canvas, TEXT("Objective"), TEXT("Find the first public lead to your sister’s recording."), FVector2D(880, 156), FVector2D(350, 77), 20, Paper);
    AddText(Canvas, TEXT("Chapter"), TEXT("Chapter I · First Contact"), FVector2D(880, 239), FVector2D(330, 24), 13, Muted);
    SpeakerText = AddText(Canvas, TEXT("Speaker"), TEXT("Ione"), FVector2D(524,470), FVector2D(90,30), 21, IoneStyle::Color(211,179,139));
    UImage* NameRule=AddImage(Canvas,TEXT("NameRule"),nullptr,FVector2D(590,483),FVector2D(614,1)); NameRule->SetColorAndOpacity(IoneStyle::Color(168,130,89,.27f));
    DialogueText = AddText(Canvas, TEXT("Dialogue"), TEXT("You’re looking for a voice. We can start with the public index.\nWhat do you remember about her last message?"), FVector2D(524,512), FVector2D(680,83), 19, Paper);
    DialogueText->SetLineHeightPercentage(1.2f);
    UImage* InputRule=AddImage(Canvas,TEXT("InputRule"),nullptr,FVector2D(524,610),FVector2D(680,1)); InputRule->SetColorAndOpacity(IoneStyle::Color(223,214,196,.15f));
    ActionCueText = AddText(Canvas, TEXT("ActionCue"), TEXT(""), FVector2D(1050.0f, 518.0f), FVector2D(170.0f, 26.0f), 16, FLinearColor(0.91f, 0.75f, 0.46f));
    InputText = WidgetTree->ConstructWidget<UEditableText>(UEditableText::StaticClass(), TEXT("PlayerInput"));
    InputText->SetHintText(FText::GetEmpty());
    FEditableTextStyle InputStyle = InputText->WidgetStyle;
    InputStyle.SetColorAndOpacity(FSlateColor(FLinearColor(0.96f, 0.92f, 0.84f)));
    InputText->SetWidgetStyle(InputStyle);
    FSlateFontInfo InputFont = IoneStyle::Font(16,true);
    InputText->SetFont(InputFont);
    UCanvasPanelSlot* InputSlot = Canvas->AddChildToCanvas(InputText);
    InputSlot->SetPosition(FVector2D(524.0f, 638.0f));
    InputSlot->SetSize(FVector2D(630.0f, 43.0f));
    InputText->OnTextCommitted.AddDynamic(this, &UAsterGameScreenWidget::HandleInputCommitted);
    InputPromptText = AddText(Canvas, TEXT("InputPrompt"), TEXT("Ask Ione anything..."),
        FVector2D(524,639), FVector2D(530,32), 16, Muted);
    InputPromptText->SetVisibility(ESlateVisibility::HitTestInvisible);
    UTextBlock* InputHint=AddText(Canvas, TEXT("InputHint"), TEXT("Enter ↵"), FVector2D(1152,641), FVector2D(65,27), 13, Muted);
    const FString SymbolFont=FPaths::Combine(FPlatformMisc::GetEnvironmentVariable(TEXT("WINDIR")),TEXT("Fonts/seguisym.ttf"));
    if(FPaths::FileExists(SymbolFont))InputHint->SetFont(FSlateFontInfo(SymbolFont,10));
    DialogueWidgets={DialogueFrame,SpeakerText,DialogueText,ActionCueText,InputText,InputPromptText,NameRule,InputRule,InputHint};
    UButton* JournalButton=WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(),TEXT("JournalButton"));
    UCanvasPanelSlot* JS=Canvas->AddChildToCanvas(JournalButton); JS->SetPosition(FVector2D(1117,32));JS->SetSize(FVector2D(112,46));
    JournalButton->SetBackgroundColor(IoneStyle::Color(16,25,27,.85f));
    IoneStyle::Button(JournalButton,FLinearColor::White);
    UTextBlock* JL=WidgetTree->ConstructWidget<UTextBlock>();JL->SetText(FText::FromString(TEXT("Journal [J]")));JL->SetFont(IoneStyle::Font(15,true));JL->SetColorAndOpacity(Paper);JournalButton->AddChild(JL);
    JournalButton->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ToggleJournal);
    JournalPanel=WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(),TEXT("JournalPanel"));
    UCanvasPanelSlot* JP=Canvas->AddChildToCanvas(JournalPanel);JP->SetPosition(FVector2D(512,94));JP->SetSize(FVector2D(717,590));
    auto Solid=[&](const TCHAR* N,FVector2D P,FVector2D S,FLinearColor C){UImage* I=AddImage(JournalPanel,N,nullptr,P,S);I->SetColorAndOpacity(C);return I;};
    Solid(TEXT("JournalBorder"),FVector2D::ZeroVector,FVector2D(717,590),IoneStyle::Color(168,130,89,.44f));
    Solid(TEXT("JournalPaper"),FVector2D(1,1),FVector2D(715,588),IoneStyle::Color(24,34,36,.96f));
    AddText(JournalPanel,TEXT("JournalTitle"),TEXT("Journal"),FVector2D(36,24),FVector2D(400,42),28,Paper);
    Solid(TEXT("JournalHeaderRule"),FVector2D(0,76),FVector2D(717,1),IoneStyle::Color(168,130,89,.25f));
    Solid(TEXT("JournalTabsRule"),FVector2D(0,130),FVector2D(717,1),IoneStyle::Color(168,130,89,.25f));
    const TCHAR* Tabs[]={TEXT("Story"),TEXT("Objectives"),TEXT("Clues"),TEXT("Memories"),TEXT("Ione")};
    const float Widths[]={55,86,57,87,55};float X=36;
    for(int32 Index=0;Index<5;Index++)
    {
        UButton* B=WidgetTree->ConstructWidget<UButton>();UCanvasPanelSlot* BS=JournalPanel->AddChildToCanvas(B);BS->SetPosition(FVector2D(X,77));BS->SetSize(FVector2D(Widths[Index],52));B->SetBackgroundColor(FLinearColor::Transparent);
        UTextBlock* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Tabs[Index]));T->SetFont(IoneStyle::Font(14,true));T->SetColorAndOpacity(Muted);B->AddChild(T);
        IoneStyle::Button(B,FLinearColor::Transparent);
        switch(Index){case 0:B->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ShowStory);break;case 1:B->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ShowObjectives);break;case 2:B->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ShowClues);break;case 3:B->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ShowMemories);break;case 4:B->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ShowIone);break;}X+=Widths[Index];
    }
    JournalUnderline=Solid(TEXT("JournalUnderline"),FVector2D(91,128),FVector2D(86,2),IoneStyle::Color(168,130,89));
    UButton* Close=WidgetTree->ConstructWidget<UButton>();UCanvasPanelSlot* CS=JournalPanel->AddChildToCanvas(Close);CS->SetPosition(FVector2D(650,22));CS->SetSize(FVector2D(40,36));Close->SetBackgroundColor(FLinearColor::Transparent);UTextBlock* CT=WidgetTree->ConstructWidget<UTextBlock>();CT->SetText(FText::FromString(TEXT("×")));CT->SetFont(IoneStyle::Font(20,true));Close->AddChild(CT);Close->OnClicked.AddDynamic(this,&UAsterGameScreenWidget::ToggleJournal);
    IoneStyle::Button(Close,FLinearColor::Transparent);
    AddText(JournalPanel,TEXT("JournalTag"),TEXT("First Contact"),FVector2D(36,171),FVector2D(600,24),13,IoneStyle::Color(201,172,135));
    JournalHeading=AddText(JournalPanel,TEXT("JournalHeading"),TEXT(""),FVector2D(36,204),FVector2D(644,44),26,Paper);
    JournalBody=AddText(JournalPanel,TEXT("JournalBody"),TEXT(""),FVector2D(36,250),FVector2D(500,65),17,Paper);JournalBody->SetLineHeightPercentage(1.2f);
    Solid(TEXT("JournalNoteRule"),FVector2D(36,324),FVector2D(590,1),IoneStyle::Color(168,130,89,.2f));
    JournalNote=AddText(JournalPanel,TEXT("JournalNote"),TEXT(""),FVector2D(36,347),FVector2D(630,90),14,Muted);
    SetJournalPage(1);JournalPanel->SetVisibility(ESlateVisibility::Collapsed);SetIsFocusable(true);
}

void UAsterGameScreenWidget::ToggleJournal()
{
    const bool Open=JournalPanel->GetVisibility()!=ESlateVisibility::Visible;
    JournalPanel->SetVisibility(Open?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    for(UWidget* Widget:DialogueWidgets)if(Widget)Widget->SetVisibility(Open?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
    InputPromptText->SetVisibility(Open?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    if(Open)SetKeyboardFocus();else if(InputText)InputText->SetKeyboardFocus();
}

FReply UAsterGameScreenWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    if((Event.GetKey()==EKeys::J && !InputText->HasKeyboardFocus()) || (Event.GetKey()==EKeys::Escape&&JournalPanel->GetVisibility()==ESlateVisibility::Visible)){ToggleJournal();return FReply::Handled();}
    return Super::NativeOnPreviewKeyDown(Geometry,Event);
}
void UAsterGameScreenWidget::ShowStory(){SetJournalPage(0);} void UAsterGameScreenWidget::ShowObjectives(){SetJournalPage(1);} void UAsterGameScreenWidget::ShowClues(){SetJournalPage(2);} void UAsterGameScreenWidget::ShowMemories(){SetJournalPage(3);} void UAsterGameScreenWidget::ShowIone(){SetJournalPage(4);}
void UAsterGameScreenWidget::SetJournalPage(int32 Page)
{
    const TCHAR* Headings[]={TEXT("A voice in the archive"),TEXT("Find the first public lead"),TEXT("No verified clues yet"),TEXT("Your search begins here"),TEXT("The sound restorer")};
    const TCHAR* Bodies[]={TEXT("The flood left the city with broken routes and scattered voices. Your sister’s final recording may be inside this archive."),TEXT("Ask Ione to check the public dispatch index for your sister’s recording."),TEXT("Clues appear here after the archive checks their source."),TEXT("You have arrived at the Archive of Forgotten Voices."),TEXT("Ione repairs damaged recordings and guides visitors through the archive.")};
    const TCHAR* Notes[]={TEXT("Ione can help you trace what the public records still know."),TEXT("Next step: type a question in the dialogue box."),TEXT("Ask Ione about the public dispatch index to begin."),TEXT("Shared events will appear as you and Ione work through the archive."),TEXT("She shares public leads and protects private voices.")};
    JournalHeading->SetText(FText::FromString(Headings[Page]));JournalBody->SetText(FText::FromString(Bodies[Page]));JournalNote->SetText(FText::FromString(Notes[Page]));
    const float X[]={36,91,177,234,321},Width[]={55,86,57,87,55};UCanvasPanelSlot* S=Cast<UCanvasPanelSlot>(JournalUnderline->Slot);S->SetPosition(FVector2D(X[Page],128));S->SetSize(FVector2D(Width[Page],2));
}

void UAsterGameScreenWidget::UpdatePortraitLayers()
{
    if (!Character) return;
    UTexture2D* Texture = Character->GetPortraitTexture();
    // All states retain the approved character design; motion is authored below.
    {
        if(UTexture2D* Selected=LoadObject<UTexture2D>(nullptr,TEXT("/Game/Character/Performance2D/Selected/Ione_Listen_Selected.Ione_Listen_Selected")))Texture=Selected;
    }
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
        InputPromptText->SetVisibility(InputText->GetText().IsEmpty() && (!JournalPanel || JournalPanel->GetVisibility()!=ESlateVisibility::Visible)
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
    if (GlowMaterial)
    {
        GlowMaterial->SetScalarParameterValue(TEXT("Lamp"), Lamp);
        GlowMaterial->SetScalarParameterValue(TEXT("Phase"), bReducedMotion ? 0.f : MotionTime);
    }
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
    // Lightweight whole-sprite gestures: speaking nod, interrupt recoil, warning lean.
    // These are 2D transforms, not skeletal animation or facial deformation.
    const float Nod = !bReducedMotion && Pose == EAsterPortraitPose::Speaking ? FMath::Sin(MotionTime * 4.f) * 1.1f : 0.f;
    const float Lean = bReducedMotion ? 0.f : Pose == EAsterPortraitPose::Warning ? -1.6f : Pose == EAsterPortraitPose::Interrupted ? 1.1f : 0.f;
    const float Shift = Accent * Pulse * 12.f;
    const float Rise = Bob - Pulse * 3.f + Nod;
    const float Angle = Lean + Nod * .35f + Accent * Pulse * 2.f;
    PortraitSlot->SetPosition(FVector2D(78.0f + Shift, 24.0f + Rise));
    PortraitImage->SetRenderTransformAngle(Angle);
    if (BackShadow)
    {
        BackShadow->SetRenderTranslation(FVector2D(Shift, Rise));
        BackShadow->SetRenderTransformAngle(Angle);
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
