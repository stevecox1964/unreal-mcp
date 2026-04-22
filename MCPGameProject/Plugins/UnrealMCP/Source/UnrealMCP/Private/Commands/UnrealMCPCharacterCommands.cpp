#include "Commands/UnrealMCPCharacterCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "MCPCharacterComponent.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "Blueprint/AIBlueprintHelperLibrary.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

FUnrealMCPCharacterCommands::FUnrealMCPCharacterCommands()
{
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // Info / Query
    if (CommandType == TEXT("get_character_status"))          return HandleGetCharacterStatus(Params);
    if (CommandType == TEXT("get_character_location"))        return HandleGetCharacterLocation(Params);
    if (CommandType == TEXT("get_character_health"))          return HandleGetCharacterHealth(Params);
    if (CommandType == TEXT("get_character_inventory"))       return HandleGetCharacterInventory(Params);
    if (CommandType == TEXT("get_character_current_action"))  return HandleGetCharacterCurrentAction(Params);
    if (CommandType == TEXT("get_character_view"))            return HandleGetCharacterView(Params);
    if (CommandType == TEXT("get_nearby_actors"))             return HandleGetNearbyActors(Params);
    if (CommandType == TEXT("get_heard_sounds"))              return HandleGetHeardSounds(Params);

    // Messaging / Memory
    if (CommandType == TEXT("send_character_message"))        return HandleSendCharacterMessage(Params);
    if (CommandType == TEXT("get_character_messages"))        return HandleGetCharacterMessages(Params);
    if (CommandType == TEXT("set_character_memory"))          return HandleSetCharacterMemory(Params);
    if (CommandType == TEXT("get_character_memory"))          return HandleGetCharacterMemory(Params);

    // Action Commands
    if (CommandType == TEXT("command_character_move_to"))     return HandleCommandMoveTo(Params);
    if (CommandType == TEXT("command_character_follow"))      return HandleCommandFollow(Params);
    if (CommandType == TEXT("command_character_stop"))        return HandleCommandStop(Params);
    if (CommandType == TEXT("command_character_look_at"))     return HandleCommandLookAt(Params);
    if (CommandType == TEXT("command_character_pickup"))      return HandleCommandPickup(Params);
    if (CommandType == TEXT("command_character_drop"))        return HandleCommandDrop(Params);
    if (CommandType == TEXT("command_character_interact"))    return HandleCommandInteract(Params);
    if (CommandType == TEXT("command_character_play_animation")) return HandleCommandPlayAnimation(Params);
    if (CommandType == TEXT("command_character_say"))         return HandleCommandSay(Params);
    if (CommandType == TEXT("command_character_set_ai_state")) return HandleCommandSetAIState(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown character command: %s"), *CommandType));
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

AActor* FUnrealMCPCharacterCommands::FindActorByName(const FString& Name) const
{
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == Name)
            return Actor;
    }
    return nullptr;
}

UMCPCharacterComponent* FUnrealMCPCharacterCommands::GetMCPComponent(AActor* Actor) const
{
    if (!Actor) return nullptr;
    return Actor->FindComponentByClass<UMCPCharacterComponent>();
}

// Shared param extraction: reads "character_name", finds actor, optionally gets component.
// Returns nullptr actor on failure and fills OutError.
static AActor* ResolveCharacter(const TSharedPtr<FJsonObject>& Params, FString& OutError)
{
    FString CharacterName;
    if (!Params->TryGetStringField(TEXT("character_name"), CharacterName))
    {
        OutError = TEXT("Missing 'character_name' parameter");
        return nullptr;
    }

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == CharacterName)
            return Actor;
    }

    OutError = FString::Printf(TEXT("Actor not found: %s"), *CharacterName);
    return nullptr;
}

static TSharedPtr<FJsonObject> MakeVec3Field(const FVector& V)
{
    TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
    Obj->SetNumberField(TEXT("x"), V.X);
    Obj->SetNumberField(TEXT("y"), V.Y);
    Obj->SetNumberField(TEXT("z"), V.Z);
    return Obj;
}

// ---------------------------------------------------------------------------
// Info / Query
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterStatus(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("name"), Actor->GetName());
    Result->SetObjectField(TEXT("location"), MakeVec3Field(Actor->GetActorLocation()));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Result->SetStringField(TEXT("ai_state"), Comp->AIState);
        Result->SetStringField(TEXT("current_action"), Comp->CurrentAction);
        Result->SetNumberField(TEXT("health"), Comp->Health);
        Result->SetStringField(TEXT("current_dialogue"), Comp->CurrentDialogue);
        Result->SetNumberField(TEXT("inbox_count"), Comp->Inbox.Num());
        Result->SetNumberField(TEXT("outbox_count"), Comp->Outbox.Num());
    }
    else
    {
        Result->SetStringField(TEXT("warning"), TEXT("No MCPCharacterComponent on actor — attach one to enable full status"));
    }

    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterLocation(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("location"), MakeVec3Field(Actor->GetActorLocation()));
    Result->SetObjectField(TEXT("rotation"), MakeVec3Field(FVector(Actor->GetActorRotation().Pitch, Actor->GetActorRotation().Yaw, Actor->GetActorRotation().Roll)));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterHealth(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("health"), Comp->Health);
    Result->SetBoolField(TEXT("is_alive"), Comp->Health > 0.0f);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterInventory(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    TArray<TSharedPtr<FJsonValue>> Items;
    for (const FString& Item : Comp->Inventory)
        Items.Add(MakeShared<FJsonValueString>(Item));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("inventory"), Items);
    Result->SetNumberField(TEXT("count"), Items.Num());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterCurrentAction(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("current_action"), Comp->CurrentAction);
    Result->SetStringField(TEXT("ai_state"), Comp->AIState);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterView(const TSharedPtr<FJsonObject>& Params)
{
    // STUB — will hook into the existing camera screenshot component
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("status"), TEXT("not_implemented"));
    Result->SetStringField(TEXT("note"), TEXT("get_character_view will be wired to the camera screenshot component in a future update"));
    TArray<TSharedPtr<FJsonValue>> Empty;
    Result->SetArrayField(TEXT("visible_actors"), Empty);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetNearbyActors(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    double Radius = 500.0;
    Params->TryGetNumberField(TEXT("radius"), Radius);

    FVector Origin = Actor->GetActorLocation();

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);

    TArray<TSharedPtr<FJsonValue>> Nearby;
    for (AActor* Other : AllActors)
    {
        if (!Other || Other == Actor) continue;
        float Dist = FVector::Dist(Origin, Other->GetActorLocation());
        if (Dist <= static_cast<float>(Radius))
        {
            TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
            Entry->SetStringField(TEXT("name"), Other->GetName());
            Entry->SetStringField(TEXT("class"), Other->GetClass()->GetName());
            Entry->SetNumberField(TEXT("distance"), Dist);
            Entry->SetObjectField(TEXT("location"), MakeVec3Field(Other->GetActorLocation()));
            Nearby.Add(MakeShared<FJsonValueObject>(Entry));
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("actors"), Nearby);
    Result->SetNumberField(TEXT("count"), Nearby.Num());
    Result->SetNumberField(TEXT("radius"), Radius);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetHeardSounds(const TSharedPtr<FJsonObject>& Params)
{
    // STUB — requires UAIPerceptionComponent with hearing config
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("status"), TEXT("not_implemented"));
    Result->SetStringField(TEXT("note"), TEXT("get_heard_sounds requires UAIPerceptionComponent with hearing configured on the character"));
    TArray<TSharedPtr<FJsonValue>> Empty;
    Result->SetArrayField(TEXT("sounds"), Empty);
    return Result;
}

// ---------------------------------------------------------------------------
// Messaging / Memory
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleSendCharacterMessage(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString Message;
    if (!Params->TryGetStringField(TEXT("message"), Message))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'message' parameter"));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    Comp->Inbox.Add(Message);
    Comp->OnMessageReceived(Message);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("message"), Message);
    Result->SetNumberField(TEXT("inbox_size"), Comp->Inbox.Num());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterMessages(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    // Default reads outbox; pass "source": "inbox" to read inbox instead
    FString Source = TEXT("outbox");
    Params->TryGetStringField(TEXT("source"), Source);

    bool bClear = false;
    Params->TryGetBoolField(TEXT("clear"), bClear);

    TArray<FString>& Queue = (Source == TEXT("inbox")) ? Comp->Inbox : Comp->Outbox;

    TArray<TSharedPtr<FJsonValue>> Messages;
    for (const FString& Msg : Queue)
        Messages.Add(MakeShared<FJsonValueString>(Msg));

    if (bClear)
        Queue.Empty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("source"), Source);
    Result->SetArrayField(TEXT("messages"), Messages);
    Result->SetNumberField(TEXT("count"), Messages.Num());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleSetCharacterMemory(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString Key, Value;
    if (!Params->TryGetStringField(TEXT("key"), Key))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'key' parameter"));
    if (!Params->TryGetStringField(TEXT("value"), Value))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'value' parameter"));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    Comp->Memory.Add(Key, Value);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("key"), Key);
    Result->SetStringField(TEXT("value"), Value);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterMemory(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);

    // Optional single-key lookup
    FString Key;
    if (Params->TryGetStringField(TEXT("key"), Key))
    {
        FString* Found = Comp->Memory.Find(Key);
        if (Found)
        {
            Result->SetStringField(TEXT("key"), Key);
            Result->SetStringField(TEXT("value"), *Found);
        }
        else
        {
            Result->SetStringField(TEXT("key"), Key);
            Result->SetBoolField(TEXT("found"), false);
        }
    }
    else
    {
        // Return full memory map
        TSharedPtr<FJsonObject> MemObj = MakeShared<FJsonObject>();
        for (const TPair<FString, FString>& Pair : Comp->Memory)
            MemObj->SetStringField(Pair.Key, Pair.Value);
        Result->SetObjectField(TEXT("memory"), MemObj);
        Result->SetNumberField(TEXT("count"), Comp->Memory.Num());
    }

    return Result;
}

// ---------------------------------------------------------------------------
// Action Commands
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandMoveTo(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    AController* Controller = Character->GetController();
    if (!Controller) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Character has no Controller — ensure an AIController is assigned"));

    FVector Destination = FVector::ZeroVector;

    if (Params->HasField(TEXT("location")))
    {
        Destination = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
        UAIBlueprintHelperLibrary::SimpleMoveToLocation(Controller, Destination);
    }
    else if (Params->HasField(TEXT("target_actor")))
    {
        FString TargetName;
        Params->TryGetStringField(TEXT("target_actor"), TargetName);
        AActor* Target = FindActorByName(TargetName);
        if (!Target) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Target actor not found: %s"), *TargetName));
        UAIBlueprintHelperLibrary::SimpleMoveToActor(Controller, Target);
        Destination = Target->GetActorLocation();
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Provide 'location' [x,y,z] or 'target_actor' name"));
    }

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Comp->AIState = TEXT("moving");
        Comp->CurrentAction = FString::Printf(TEXT("moving_to [%.0f, %.0f, %.0f]"), Destination.X, Destination.Y, Destination.Z);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("destination"), MakeVec3Field(Destination));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandFollow(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString TargetName;
    if (!Params->TryGetStringField(TEXT("target_actor"), TargetName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'target_actor' parameter"));

    AActor* Target = FindActorByName(TargetName);
    if (!Target) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Target actor not found: %s"), *TargetName));

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    AController* Controller = Character->GetController();
    if (!Controller) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Character has no Controller"));

    UAIBlueprintHelperLibrary::SimpleMoveToActor(Controller, Target);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Comp->AIState = TEXT("following");
        Comp->CurrentAction = FString::Printf(TEXT("following_%s"), *TargetName);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("following"), TargetName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandStop(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    AAIController* AIController = Cast<AAIController>(Character->GetController());
    if (AIController)
        AIController->StopMovement();

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Comp->AIState = TEXT("idle");
        Comp->CurrentAction = TEXT("stopped");
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandLookAt(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FVector TargetLocation = FVector::ZeroVector;

    if (Params->HasField(TEXT("location")))
    {
        TargetLocation = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    else if (Params->HasField(TEXT("target_actor")))
    {
        FString TargetName;
        Params->TryGetStringField(TEXT("target_actor"), TargetName);
        AActor* Target = FindActorByName(TargetName);
        if (!Target) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Target actor not found: %s"), *TargetName));
        TargetLocation = Target->GetActorLocation();
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Provide 'location' or 'target_actor'"));
    }

    FVector Direction = TargetLocation - Actor->GetActorLocation();
    Direction.Z = 0.0f;
    if (!Direction.IsNearlyZero())
        Actor->SetActorRotation(Direction.Rotation());

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("looking_at"), MakeVec3Field(TargetLocation));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandPickup(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString ItemName;
    if (!Params->TryGetStringField(TEXT("item_name"), ItemName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'item_name' parameter"));

    AActor* ItemActor = FindActorByName(ItemName);
    if (!ItemActor) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Item actor not found: %s"), *ItemName));

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    // Use "hand_r" socket if the mesh has it, otherwise attach to root
    FString SocketName = TEXT("hand_r");
    Params->TryGetStringField(TEXT("socket"), SocketName);

    USkeletalMeshComponent* Mesh = Character->GetMesh();
    FAttachmentTransformRules AttachRules(EAttachmentRule::SnapToTarget, EAttachmentRule::SnapToTarget, EAttachmentRule::KeepRelative, true);

    if (Mesh && Mesh->DoesSocketExist(FName(*SocketName)))
        ItemActor->AttachToComponent(Mesh, AttachRules, FName(*SocketName));
    else
        ItemActor->AttachToActor(Actor, FAttachmentTransformRules(EAttachmentRule::SnapToTarget, true));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Comp->Inventory.AddUnique(ItemName);
        Comp->CurrentAction = FString::Printf(TEXT("picked_up_%s"), *ItemName);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("picked_up"), ItemName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandDrop(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    // Optional: drop a specific item, or drop all
    FString ItemName;
    bool bDropSpecific = Params->TryGetStringField(TEXT("item_name"), ItemName);

    TArray<AActor*> Attached;
    Actor->GetAttachedActors(Attached);

    TArray<FString> Dropped;
    FDetachmentTransformRules DetachRules(EDetachmentRule::KeepWorld, true);

    for (AActor* Attached_Actor : Attached)
    {
        if (!bDropSpecific || Attached_Actor->GetName() == ItemName)
        {
            Attached_Actor->DetachFromActor(DetachRules);
            Dropped.Add(Attached_Actor->GetName());
        }
    }

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        for (const FString& DroppedName : Dropped)
            Comp->Inventory.Remove(DroppedName);
        if (!Dropped.IsEmpty())
            Comp->CurrentAction = TEXT("dropped_item");
    }

    TArray<TSharedPtr<FJsonValue>> DroppedArr;
    for (const FString& Name : Dropped)
        DroppedArr.Add(MakeShared<FJsonValueString>(Name));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("dropped"), DroppedArr);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandInteract(const TSharedPtr<FJsonObject>& Params)
{
    // STUB — fires OnInteractRequested on the component; game implements the interaction in Blueprint
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString TargetName;
    Params->TryGetStringField(TEXT("target_actor"), TargetName);

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
    {
        Comp->OnInteractRequested(TargetName);
        Comp->CurrentAction = FString::Printf(TEXT("interacting_with_%s"), *TargetName);
        Comp->AIState = TEXT("interacting");
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("status"), TEXT("interact_event_fired"));
    Result->SetStringField(TEXT("note"), TEXT("Implement OnInteractRequested in the NPC Blueprint to handle the interaction"));
    Result->SetStringField(TEXT("target_actor"), TargetName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandPlayAnimation(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString MontagePath;
    if (!Params->TryGetStringField(TEXT("montage_path"), MontagePath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'montage_path' parameter (full asset path, e.g. /Game/Animations/AM_Wave)"));

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    USkeletalMeshComponent* Mesh = Character->GetMesh();
    if (!Mesh) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Character has no SkeletalMeshComponent"));

    UAnimInstance* AnimInst = Mesh->GetAnimInstance();
    if (!AnimInst) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Character has no AnimInstance"));

    UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, *MontagePath);
    if (!Montage) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("AnimMontage not found at path: %s"), *MontagePath));

    double PlayRate = 1.0;
    Params->TryGetNumberField(TEXT("play_rate"), PlayRate);

    float Duration = AnimInst->Montage_Play(Montage, static_cast<float>(PlayRate));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (Comp)
        Comp->CurrentAction = FString::Printf(TEXT("playing_animation_%s"), *Montage->GetName());

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("montage"), Montage->GetName());
    Result->SetNumberField(TEXT("duration"), Duration);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandSay(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString Text;
    if (!Params->TryGetStringField(TEXT("text"), Text))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'text' parameter"));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    Comp->CurrentDialogue = Text;
    Comp->Outbox.Add(Text);
    Comp->OnSayRequested(Text);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("text"), Text);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandSetAIState(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    FString NewState;
    if (!Params->TryGetStringField(TEXT("state"), NewState))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'state' parameter (idle, moving, in_combat, interacting, following, fleeing)"));

    UMCPCharacterComponent* Comp = GetMCPComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No MCPCharacterComponent on: %s"), *Actor->GetName()));

    Comp->AIState = NewState;
    Comp->OnAIStateChanged(NewState);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("ai_state"), NewState);
    return Result;
}
