#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "APCCharacterComponent.generated.h"

/**
 * Add this component to any APC (agent) Blueprint to enable character commands.
 * Stores inbox/outbox message queues, a key-value memory store, and runtime state
 * that the sim server reads and writes via TCP commands.
 */
UCLASS(ClassGroup=(APC), meta=(BlueprintSpawnableComponent))
class UNREALMCP_API UAPCCharacterComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UAPCCharacterComponent();

    // --- Messaging ---

    /** Messages sent to this character from the sim (send_character_message). */
    UPROPERTY(BlueprintReadWrite, Category="APC|Messaging")
    TArray<FString> Inbox;

    /** Messages this character sends back to the sim (get_character_messages). */
    UPROPERTY(BlueprintReadWrite, Category="APC|Messaging")
    TArray<FString> Outbox;

    // --- Memory ---

    /** Arbitrary key-value facts the character remembers (set/get_character_memory). */
    UPROPERTY(BlueprintReadWrite, Category="APC|Memory")
    TMap<FString, FString> Memory;

    // --- Runtime State ---

    /** Current AI state label: idle, moving, in_combat, interacting, following, fleeing. */
    UPROPERTY(BlueprintReadWrite, Category="APC|State")
    FString AIState;

    /** Human-readable description of the current action. */
    UPROPERTY(BlueprintReadWrite, Category="APC|State")
    FString CurrentAction;

    /** Character health value — set this from your damage system. */
    UPROPERTY(BlueprintReadWrite, Category="APC|State")
    float Health;

    /** Names of actors currently carried by this character. */
    UPROPERTY(BlueprintReadWrite, Category="APC|State")
    TArray<FString> Inventory;

    /** Last line of dialogue set via command_character_say. */
    UPROPERTY(BlueprintReadWrite, Category="APC|State")
    FString CurrentDialogue;

    // --- Blueprint Events (implement in the APC Blueprint) ---

    /** Fired when a message arrives in the Inbox. Wire this to your dialogue/AI logic. */
    UFUNCTION(BlueprintImplementableEvent, Category="APC|Messaging")
    void OnMessageReceived(const FString& Message);

    /** Fired when command_character_set_ai_state is called. */
    UFUNCTION(BlueprintImplementableEvent, Category="APC|State")
    void OnAIStateChanged(const FString& NewState);

    /** Fired when command_character_interact is called. Implement the interaction in Blueprint. */
    UFUNCTION(BlueprintImplementableEvent, Category="APC|Actions")
    void OnInteractRequested(const FString& TargetActorName);

    /** Fired when command_character_say is called. Use this to drive your dialogue UI. */
    UFUNCTION(BlueprintImplementableEvent, Category="APC|Actions")
    void OnSayRequested(const FString& Text);
};
