#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for character-related MCP commands.
 * Covers messaging, memory, status queries, and action commands (move, pickup, etc.).
 * Requires UMCPCharacterComponent to be present on the target actor for state commands.
 */
class UNREALMCP_API FUnrealMCPCharacterCommands
{
public:
    FUnrealMCPCharacterCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    // --- Helpers ---
    AActor* FindActorByName(const FString& Name) const;
    class UMCPCharacterComponent* GetMCPComponent(AActor* Actor) const;

    // --- Info / Query ---
    TSharedPtr<FJsonObject> HandleGetCharacterStatus(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterLocation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterHealth(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterInventory(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterCurrentAction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterView(const TSharedPtr<FJsonObject>& Params);         // stub
    TSharedPtr<FJsonObject> HandleGetNearbyActors(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetHeardSounds(const TSharedPtr<FJsonObject>& Params);           // stub

    // --- Messaging / Memory ---
    TSharedPtr<FJsonObject> HandleSendCharacterMessage(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterMessages(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetCharacterMemory(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetCharacterMemory(const TSharedPtr<FJsonObject>& Params);

    // --- Action Commands ---
    TSharedPtr<FJsonObject> HandleCommandMoveTo(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandFollow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandStop(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandLookAt(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandPickup(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandDrop(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandInteract(const TSharedPtr<FJsonObject>& Params);          // stub
    TSharedPtr<FJsonObject> HandleCommandPlayAnimation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandSay(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCommandSetAIState(const TSharedPtr<FJsonObject>& Params);
};
