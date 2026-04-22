#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "MCPCharacterComponent.generated.h"

/**
 * Add this component to any NPC Blueprint to enable MCP character commands.
 * Stores inbox/outbox message queues, a key-value memory store, and runtime state
 * that the MCP server reads and writes via TCP commands.
 */
UCLASS(ClassGroup=(MCP), meta=(BlueprintSpawnableComponent))
class UNREALMCP_API UMCPCharacterComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UMCPCharacterComponent();

    // --- Messaging ---

    /** Messages sent to this character from MCP (send_character_message). */
    UPROPERTY(BlueprintReadWrite, Category="MCP|Messaging")
    TArray<FString> Inbox;

    /** Messages this character sends back to MCP (get_character_messages). */
    UPROPERTY(BlueprintReadWrite, Category="MCP|Messaging")
    TArray<FString> Outbox;

    // --- Memory ---

    /** Arbitrary key-value facts the character remembers (set/get_character_memory). */
    UPROPERTY(BlueprintReadWrite, Category="MCP|Memory")
    TMap<FString, FString> Memory;

    // --- Runtime State ---

    /** Current AI state label: idle, moving, in_combat, interacting, following, fleeing. */
    UPROPERTY(BlueprintReadWrite, Category="MCP|State")
    FString AIState;

    /** Human-readable description of the current action. */
    UPROPERTY(BlueprintReadWrite, Category="MCP|State")
    FString CurrentAction;

    /** Character health value — set this from your damage system. */
    UPROPERTY(BlueprintReadWrite, Category="MCP|State")
    float Health;

    /** Names of actors currently carried by this character. */
    UPROPERTY(BlueprintReadWrite, Category="MCP|State")
    TArray<FString> Inventory;

    /** Last line of dialogue set via command_character_say. */
    UPROPERTY(BlueprintReadWrite, Category="MCP|State")
    FString CurrentDialogue;

    // --- Blueprint Events (implement in the NPC Blueprint) ---

    /** Fired when a message arrives in the Inbox. Wire this to your dialogue/AI logic. */
    UFUNCTION(BlueprintImplementableEvent, Category="MCP|Messaging")
    void OnMessageReceived(const FString& Message);

    /** Fired when command_character_set_ai_state is called. */
    UFUNCTION(BlueprintImplementableEvent, Category="MCP|State")
    void OnAIStateChanged(const FString& NewState);

    /** Fired when command_character_interact is called. Implement the interaction in Blueprint. */
    UFUNCTION(BlueprintImplementableEvent, Category="MCP|Actions")
    void OnInteractRequested(const FString& TargetActorName);

    /** Fired when command_character_say is called. Use this to drive your dialogue UI. */
    UFUNCTION(BlueprintImplementableEvent, Category="MCP|Actions")
    void OnSayRequested(const FString& Text);
};
