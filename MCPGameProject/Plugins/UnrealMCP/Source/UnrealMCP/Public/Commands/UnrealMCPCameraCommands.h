#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * MCP command handler for camera capture operations.
 * Finds ACameraCaptureActor instances in the level and triggers image saves.
 */
class UNREALMCP_API FUnrealMCPCameraCommands
{
public:
    FUnrealMCPCameraCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCaptureImage(const TSharedPtr<FJsonObject>& Params);
};
