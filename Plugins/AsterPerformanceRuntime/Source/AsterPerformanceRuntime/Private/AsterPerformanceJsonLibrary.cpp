#include "AsterPerformanceJsonLibrary.h"

#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

bool UAsterPerformanceJsonLibrary::ParsePerformanceRequest(
    const FString& Json,
    FAsterPerformanceRequest& OutRequest,
    FString& OutError)
{
    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        OutError = TEXT("Invalid JSON document.");
        return false;
    }

    if (!Root->TryGetStringField(TEXT("dialogue"), OutRequest.Dialogue) || OutRequest.Dialogue.IsEmpty())
    {
        OutError = TEXT("Required field 'dialogue' is missing or empty.");
        return false;
    }

    const TArray<TSharedPtr<FJsonValue>>* Anchors = nullptr;
    if (!Root->TryGetArrayField(TEXT("semantic_anchors"), Anchors) || Anchors == nullptr)
    {
        OutError = TEXT("Required array 'semantic_anchors' is missing.");
        return false;
    }

    OutRequest.SemanticAnchors.Reset();
    for (int32 Index = 0; Index < Anchors->Num(); ++Index)
    {
        const TSharedPtr<FJsonObject> AnchorJson = (*Anchors)[Index]->AsObject();
        if (!AnchorJson.IsValid())
        {
            OutError = FString::Printf(TEXT("semantic_anchors[%d] must be an object."), Index);
            return false;
        }

        FString Function;
        double TriggerSeconds = 0.0;
        double Confidence = 1.0;
        if (!AnchorJson->TryGetStringField(TEXT("function"), Function) || Function.IsEmpty()
            || !AnchorJson->TryGetNumberField(TEXT("trigger_seconds"), TriggerSeconds))
        {
            OutError = FString::Printf(TEXT("semantic_anchors[%d] lacks function or trigger_seconds."), Index);
            return false;
        }
        AnchorJson->TryGetNumberField(TEXT("confidence"), Confidence);

        FAsterSemanticAnchor Anchor;
        Anchor.Function = FName(*Function);
        Anchor.TriggerSeconds = FMath::Max(0.0, TriggerSeconds);
        Anchor.Confidence = FMath::Clamp(Confidence, 0.0, 1.0);
        FString WorldTarget;
        if (AnchorJson->TryGetStringField(TEXT("world_target"), WorldTarget))
        {
            Anchor.WorldTarget = FName(*WorldTarget);
        }
        OutRequest.SemanticAnchors.Add(Anchor);
    }

    OutError.Reset();
    return true;
}
