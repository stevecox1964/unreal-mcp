#include "Commands/UnrealMCPAttachmentCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "Components/SkeletalMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

FUnrealMCPAttachmentCommands::FUnrealMCPAttachmentCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPAttachmentCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("attach_actor_to_actor")) return HandleAttachActorToActor(Params);
    if (CommandType == TEXT("detach_actor"))          return HandleDetachActor(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown attachment command: %s"), *CommandType));
}

AActor* FUnrealMCPAttachmentCommands::FindActorByName(const FString& Name) const
{
    return FUnrealMCPCommonUtils::FindActorByNameOrLabel(GWorld, Name);
}

TSharedPtr<FJsonObject> FUnrealMCPAttachmentCommands::HandleAttachActorToActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ChildName;
    if (!Params->TryGetStringField(TEXT("child_actor"), ChildName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'child_actor' parameter"));

    FString ParentName;
    if (!Params->TryGetStringField(TEXT("parent_actor"), ParentName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'parent_actor' parameter"));

    AActor* ChildActor = FindActorByName(ChildName);
    if (!ChildActor) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Child actor not found: %s"), *ChildName));

    AActor* ParentActor = FindActorByName(ParentName);
    if (!ParentActor) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Parent actor not found: %s"), *ParentName));

    if (ChildActor == ParentActor)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Cannot attach an actor to itself"));

    FString SocketName;
    Params->TryGetStringField(TEXT("socket"), SocketName);

    bool bWeldSimulatedBodies = true;
    Params->TryGetBoolField(TEXT("weld_simulated_bodies"), bWeldSimulatedBodies);

    FAttachmentTransformRules AttachRules(EAttachmentRule::SnapToTarget,
                                          EAttachmentRule::SnapToTarget,
                                          EAttachmentRule::KeepRelative,
                                          bWeldSimulatedBodies);

    USkeletalMeshComponent* Mesh = nullptr;
    if (ACharacter* Character = Cast<ACharacter>(ParentActor))
        Mesh = Character->GetMesh();

    bool bAttachedToSocket = false;
    if (!SocketName.IsEmpty() && Mesh && Mesh->DoesSocketExist(FName(*SocketName)))
    {
        ChildActor->AttachToComponent(Mesh, AttachRules, FName(*SocketName));
        bAttachedToSocket = true;
    }
    else
    {
        ChildActor->AttachToActor(ParentActor, AttachRules);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("child_actor"), ChildName);
    Result->SetStringField(TEXT("parent_actor"), ParentName);
    Result->SetBoolField(TEXT("attached_to_socket"), bAttachedToSocket);
    if (bAttachedToSocket)
        Result->SetStringField(TEXT("socket"), SocketName);
    else if (!SocketName.IsEmpty())
        Result->SetStringField(TEXT("note"), FString::Printf(TEXT("Socket '%s' not found on parent; attached to root component"), *SocketName));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPAttachmentCommands::HandleDetachActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));

    AActor* Actor = FindActorByName(ActorName);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    FDetachmentTransformRules DetachRules(EDetachmentRule::KeepWorld, true);
    Actor->DetachFromActor(DetachRules);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    return Result;
}
