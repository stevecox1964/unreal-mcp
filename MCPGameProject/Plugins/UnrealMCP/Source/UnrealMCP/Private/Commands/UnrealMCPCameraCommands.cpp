#include "Commands/UnrealMCPCameraCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "CameraCaptureActor.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "Misc/DateTime.h"

FUnrealMCPCameraCommands::FUnrealMCPCameraCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPCameraCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("capture_camera_image"))
        return HandleCaptureImage(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown camera command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPCameraCommands::HandleCaptureImage(const TSharedPtr<FJsonObject>& Params)
{
    ACameraCaptureActor* CaptureActor = nullptr;

    // If caller specifies an actor name, find that one; otherwise grab the first in the level.
    FString ActorName;
    if (Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        TArray<AActor*> AllActors;
        UGameplayStatics::GetAllActorsOfClass(GWorld, ACameraCaptureActor::StaticClass(), AllActors);
        for (AActor* Actor : AllActors)
        {
            if (Actor && Actor->GetName() == ActorName)
            {
                CaptureActor = Cast<ACameraCaptureActor>(Actor);
                break;
            }
        }
        if (!CaptureActor)
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("CameraCaptureActor not found: %s"), *ActorName));
    }
    else
    {
        TArray<AActor*> AllActors;
        UGameplayStatics::GetAllActorsOfClass(GWorld, ACameraCaptureActor::StaticClass(), AllActors);
        if (AllActors.Num() == 0)
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                TEXT("No CameraCaptureActor found in level. Place one and run the map."));
        CaptureActor = Cast<ACameraCaptureActor>(AllActors[0]);
    }

    if (!CaptureActor)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to resolve CameraCaptureActor"));

    FString SafeName = CaptureActor->GetName().Replace(TEXT(" "), TEXT("_"));
    FString Timestamp = FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"));
    FString FileName = FString::Printf(TEXT("%s_%s.png"), *SafeName, *Timestamp);

    CaptureActor->SaveCameraImageToFile(FileName);

    FString FilePath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() + FileName);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), CaptureActor->GetName());
    Result->SetStringField(TEXT("file_path"), FilePath);
    return Result;
}
