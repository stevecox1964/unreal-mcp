#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for actor attachment MCP commands.
 * Provides a generic primitive to parent any AActor under any other AActor,
 * optionally snapping to a named socket on the parent's SkeletalMesh.
 */
class UNREALMCP_API FUnrealMCPAttachmentCommands
{
public:
    FUnrealMCPAttachmentCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    AActor* FindActorByName(const FString& Name) const;

    TSharedPtr<FJsonObject> HandleAttachActorToActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDetachActor(const TSharedPtr<FJsonObject>& Params);
};
