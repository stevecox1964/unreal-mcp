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

    // If caller specifies an actor name: try direct cast first, then search attached children.
    // This lets callers pass the owning NPC actor name rather than the camera actor name.
    // If no actor_name given, fall back to the first CameraCaptureActor in the level.
    FString ActorName;
    if (Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        AActor* Found = FUnrealMCPCommonUtils::FindActorByNameOrLabel(GWorld, ActorName);
        if (!Found)
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Actor not found: %s"), *ActorName));

        CaptureActor = Cast<ACameraCaptureActor>(Found);
        if (!CaptureActor)
        {
            TArray<AActor*> Attached;
            Found->GetAttachedActors(Attached);
            for (AActor* Child : Attached)
            {
                CaptureActor = Cast<ACameraCaptureActor>(Child);
                if (CaptureActor) break;
            }
        }

        if (!CaptureActor)
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("No CameraCaptureActor found on or attached to: %s"), *ActorName));
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

    // Caller may provide an absolute file_path (e.g. agent observations folder).
    // If not, fall back to <ProjectDir>/<ActorName>_<timestamp>.png.
    FString FilePath;
    if (!Params->TryGetStringField(TEXT("file_path"), FilePath) || FilePath.IsEmpty())
    {
        FString SafeName = CaptureActor->GetName().Replace(TEXT(" "), TEXT("_"));
        FString Timestamp = FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"));
        FilePath = FPaths::ConvertRelativePathToFull(
            FPaths::ProjectDir() + FString::Printf(TEXT("%s_%s.png"), *SafeName, *Timestamp));
    }

    CaptureActor->SaveCameraImageToFile(FilePath);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), CaptureActor->GetName());
    Result->SetStringField(TEXT("file_path"), FilePath);
    return Result;
}
