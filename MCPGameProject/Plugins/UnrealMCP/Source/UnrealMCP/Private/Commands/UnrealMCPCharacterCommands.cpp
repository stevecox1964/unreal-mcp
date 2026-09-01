#include "Commands/UnrealMCPCharacterCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "APCCharacterComponent.h"
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
#include "Components/CapsuleComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "GameFramework/Pawn.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"

FUnrealMCPCharacterCommands::FUnrealMCPCharacterCommands()
{
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // Info / Query
    if (CommandType == TEXT("get_character_forward_trace"))   return HandleGetCharacterForwardTrace(Params);
    if (CommandType == TEXT("get_character_forward_volume"))  return HandleGetCharacterForwardVolume(Params);
    if (CommandType == TEXT("get_character_radar"))           return HandleGetCharacterRadar(Params);
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
    if (CommandType == TEXT("command_character_teleport"))    return HandleCommandTeleport(Params);
    if (CommandType == TEXT("command_character_look_at"))     return HandleCommandLookAt(Params);
    if (CommandType == TEXT("command_character_pickup"))      return HandleCommandPickup(Params);
    if (CommandType == TEXT("command_character_drop"))        return HandleCommandDrop(Params);
    if (CommandType == TEXT("command_character_interact"))    return HandleCommandInteract(Params);
    if (CommandType == TEXT("command_character_play_animation")) return HandleCommandPlayAnimation(Params);
    if (CommandType == TEXT("command_character_say"))         return HandleCommandSay(Params);
    if (CommandType == TEXT("command_character_set_ai_state")) return HandleCommandSetAIState(Params);
    if (CommandType == TEXT("command_character_step_to_ground")) return HandleCommandStepToGround(Params); // #101

    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown character command: %s"), *CommandType));
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

AActor* FUnrealMCPCharacterCommands::FindActorByName(const FString& Name) const
{
    return FUnrealMCPCommonUtils::FindActorByNameOrLabel(FUnrealMCPCommonUtils::GetGameWorld(), Name);
}

UAPCCharacterComponent* FUnrealMCPCharacterCommands::GetAPCComponent(AActor* Actor) const
{
    if (!Actor) return nullptr;
    return Actor->FindComponentByClass<UAPCCharacterComponent>();
}

// Shared param extraction: reads "character_name", finds actor, optionally gets component.
// Returns nullptr actor on failure and fills OutError.
// Resolves by GetName() OR GetActorLabel() so callers can use friendly Outliner names.
static AActor* ResolveCharacter(const TSharedPtr<FJsonObject>& Params, FString& OutError)
{
    FString CharacterName;
    if (!Params->TryGetStringField(TEXT("character_name"), CharacterName))
    {
        OutError = TEXT("Missing 'character_name' parameter");
        return nullptr;
    }

    if (AActor* Actor = FUnrealMCPCommonUtils::FindActorByNameOrLabel(FUnrealMCPCommonUtils::GetGameWorld(), CharacterName))
        return Actor;

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
// Lizard-brain senses
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterForwardTrace(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UWorld* World = Actor->GetWorld();
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No world"));

    double DistanceCm = 300.0;
    Params->TryGetNumberField(TEXT("distance_cm"), DistanceCm);

    // Eye-height offset keeps the trace from clipping the ground
    FVector Start = Actor->GetActorLocation() + FVector(0.0f, 0.0f, 60.0f);
    FVector End   = Start + Actor->GetActorForwardVector() * (float)DistanceCm;

    FHitResult Hit;
    FCollisionQueryParams QueryParams(TEXT("ForwardTrace"), false, Actor);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);

    if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, QueryParams))
    {
        AActor* HitActor = Hit.GetActor();
        Result->SetBoolField(TEXT("hit"), true);
        Result->SetStringField(TEXT("actor_name"),  HitActor ? HitActor->GetActorLabel() : TEXT("unknown"));
        Result->SetStringField(TEXT("actor_class"), HitActor ? HitActor->GetClass()->GetName() : TEXT("unknown"));
        Result->SetNumberField(TEXT("distance_cm"), (double)Hit.Distance);
    }
    else
    {
        Result->SetBoolField(TEXT("hit"), false);
    }
    return Result;
}

// ---------------------------------------------------------------------------
// #81 — the body-box probe. "Can I fit", not "can a line pass".
//
// HandleGetCharacterForwardTrace above is one infinitely thin ray, at hip
// height, on ECC_Visibility. It has no width (a post 30 cm off-centre is struck
// by the shoulder and never by the ray), no height (a kerb at 30 cm and an awning
// at 210 cm are both invisible), and it asks the wrong question — Visibility
// answers "what can I see", while movement is stopped by ECC_Pawn, which is
// exactly where blocking volumes and invisible prop collision live.
//
// This handler answers the two questions the user actually asked, in one round
// trip because the bridge is a single socket:
//
//   1. "Can I fit?"      — a capsule sweep using the character's OWN capsule.
//                          If the swept body contacts nothing, it fits, by
//                          construction. Also yields the honest clearance.
//   2. "Where's the gap?" — a coarse ray raster across the body's frontal
//                          rectangle (columns x rows), which is the left-to-right
//                          / top-to-bottom scan. The sweep gives one yes/no; only
//                          the raster can say "clear left, blocked right".
//
// Every hit also reports engine-side identity signals (physical material,
// component class, actor tags) so Python can classify without reading the level
// author's file names — see backlog #83.
// ---------------------------------------------------------------------------

// Identity signals for one hit, gathered engine-side so the Python classifier is
// not reduced to substring-matching whatever the level author called the asset.
static void FillHitIdentity(const FHitResult& Hit, const TSharedPtr<FJsonObject>& Out)
{
    AActor* HitActor = Hit.GetActor();
    Out->SetStringField(TEXT("actor_name"),  HitActor ? HitActor->GetActorLabel() : TEXT("unknown"));
    Out->SetStringField(TEXT("actor_class"), HitActor ? HitActor->GetClass()->GetName() : TEXT("unknown"));
    Out->SetNumberField(TEXT("distance_cm"), (double)Hit.Distance);

    // Physical material is set by the art pipeline, not by whoever typed the
    // actor label, so it survives renaming and marketplace packs (#83).
    if (Hit.PhysMaterial.IsValid())
    {
        Out->SetStringField(TEXT("physical_material"), Hit.PhysMaterial->GetName());
    }
    if (Hit.GetComponent())
    {
        Out->SetStringField(TEXT("component_class"), Hit.GetComponent()->GetClass()->GetName());
        Out->SetStringField(TEXT("collision_profile"),
                            Hit.GetComponent()->GetCollisionProfileName().ToString());
        Out->SetBoolField(TEXT("is_movable"),
                          Hit.GetComponent()->Mobility == EComponentMobility::Movable);
    }
    // Tags are the author's deliberate semantic statement — unlike the asset
    // name, which is just a file name.
    if (HitActor && HitActor->Tags.Num() > 0)
    {
        TArray<TSharedPtr<FJsonValue>> TagValues;
        for (const FName& Tag : HitActor->Tags)
        {
            TagValues.Add(MakeShared<FJsonValueString>(Tag.ToString()));
        }
        Out->SetArrayField(TEXT("tags"), TagValues);
    }
    Out->SetBoolField(TEXT("is_pawn"), HitActor && HitActor->IsA(APawn::StaticClass()));
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterForwardVolume(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UWorld* World = Actor->GetWorld();
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No world"));

    double DistanceCm = 500.0;
    Params->TryGetNumberField(TEXT("distance_cm"), DistanceCm);

    // The probe may be aimed off the body's facing so one call can ask about
    // "forward-left" without turning the character first.
    double YawOffsetDeg = 0.0;
    Params->TryGetNumberField(TEXT("yaw_offset_deg"), YawOffsetDeg);

    int32 Columns = 5;
    int32 Rows = 3;
    { int32 V = 0; if (Params->TryGetNumberField(TEXT("columns"), V) && V > 0 && V <= 15) Columns = V; }
    { int32 V = 0; if (Params->TryGetNumberField(TEXT("rows"),    V) && V > 0 && V <= 15) Rows    = V; }

    // Read the real capsule rather than hard-coding a body size; log it once so a
    // mismatch is visible instead of silently wrong.
    float Radius = 34.0f;
    float HalfHeight = 88.0f;
    bool bCapsuleFromEngine = false;
    if (ACharacter* AsCharacter = Cast<ACharacter>(Actor))
    {
        if (UCapsuleComponent* Capsule = AsCharacter->GetCapsuleComponent())
        {
            Radius = Capsule->GetScaledCapsuleRadius();
            HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
            bCapsuleFromEngine = true;
        }
    }

    // A forward sweep at full body height calls every kerb a wall. Lift the probe
    // by the character's own step height so ground it can simply walk up is not
    // reported as a blockage.
    float StepUpCm = 45.0f;
    if (ACharacter* AsCharacter = Cast<ACharacter>(Actor))
    {
        if (UCharacterMovementComponent* Move = AsCharacter->GetCharacterMovement())
        {
            StepUpCm = Move->MaxStepHeight;
        }
    }

    const FRotator ProbeRotation = Actor->GetActorRotation() + FRotator(0.0f, (float)YawOffsetDeg, 0.0f);
    const FVector Forward = ProbeRotation.Vector().GetSafeNormal();
    const FVector Right   = FRotationMatrix(ProbeRotation).GetScaledAxis(EAxis::Y);
    const FVector Up      = FVector::UpVector;

    // Sweep from a start lifted by the step height, with the swept capsule
    // shortened by the same amount so its bottom sits at the top of a step the
    // character could climb anyway.
    const float SweepHalfHeight = FMath::Max(HalfHeight - StepUpCm * 0.5f, Radius + 1.0f);
    const FVector Base  = Actor->GetActorLocation();
    const FVector Start = Base + Up * (StepUpCm * 0.5f);
    const FVector End   = Start + Forward * (float)DistanceCm;

    FCollisionQueryParams QueryParams(TEXT("ForwardVolume"), /*bTraceComplex=*/false, Actor);
    QueryParams.bReturnPhysicalMaterial = true;

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("body_radius_cm"), (double)Radius);
    Result->SetNumberField(TEXT("body_half_height_cm"), (double)HalfHeight);
    Result->SetBoolField(TEXT("capsule_from_engine"), bCapsuleFromEngine);
    Result->SetNumberField(TEXT("step_up_cm"), (double)StepUpCm);
    Result->SetNumberField(TEXT("distance_cm"), DistanceCm);
    Result->SetNumberField(TEXT("yaw_offset_deg"), YawOffsetDeg);
    Result->SetNumberField(TEXT("columns"), Columns);
    Result->SetNumberField(TEXT("rows"), Rows);

    // ---- 1. Can the body fit? ----------------------------------------------
    // ECC_Pawn is the honest movement question: it is what actually stops this
    // body, including blocking volumes that ECC_Visibility cannot see.
    FHitResult SweepHit;
    const bool bSweepBlocked = World->SweepSingleByChannel(
        SweepHit, Start, End, ProbeRotation.Quaternion(), ECC_Pawn,
        FCollisionShape::MakeCapsule(Radius, SweepHalfHeight), QueryParams);

    Result->SetBoolField(TEXT("fits"), !bSweepBlocked);
    Result->SetNumberField(TEXT("clearance_cm"),
                           bSweepBlocked ? (double)SweepHit.Distance : DistanceCm);
    if (bSweepBlocked)
    {
        TSharedPtr<FJsonObject> Contact = MakeShared<FJsonObject>();
        FillHitIdentity(SweepHit, Contact);
        Result->SetObjectField(TEXT("contact"), Contact);
    }

    // ---- 2. Where is the gap? ----------------------------------------------
    // A coarse raster across the body's frontal rectangle: left-to-right by
    // column, bottom-to-top by row. Columns are reported in body-relative terms
    // so Python never has to reason about world axes.
    TArray<TSharedPtr<FJsonValue>> OpenColumns;
    TArray<TSharedPtr<FJsonValue>> BlockedColumns;
    TArray<TSharedPtr<FJsonValue>> OpenRows;
    TArray<TSharedPtr<FJsonValue>> CellRows;
    int32 BlockedCells = 0;
    int32 TotalCells = Columns * Rows;
    float NearestCm = (float)DistanceCm;

    // Column labels for a 5-wide raster; generated positionally for other widths.
    auto ColumnLabel = [Columns](int32 Index) -> FString
    {
        if (Columns == 5)
        {
            static const TCHAR* Names[5] = { TEXT("far_left"), TEXT("left"), TEXT("centre"),
                                             TEXT("right"), TEXT("far_right") };
            return FString(Names[Index]);
        }
        if (Columns == 3)
        {
            static const TCHAR* Names[3] = { TEXT("left"), TEXT("centre"), TEXT("right") };
            return FString(Names[Index]);
        }
        return FString::Printf(TEXT("col_%d"), Index);
    };
    auto RowLabel = [Rows](int32 Index) -> FString
    {
        if (Rows == 3)
        {
            static const TCHAR* Names[3] = { TEXT("low"), TEXT("mid"), TEXT("high") };
            return FString(Names[Index]);
        }
        return FString::Printf(TEXT("row_%d"), Index);
    };

    for (int32 Col = 0; Col < Columns; ++Col)
    {
        // Spread sample points across the full body width, edge to edge.
        const float ColT = (Columns == 1) ? 0.0f
                         : ((float)Col / (float)(Columns - 1)) * 2.0f - 1.0f;   // -1 .. +1
        const FVector ColOffset = Right * (ColT * Radius);

        bool bColumnOpen = false;
        for (int32 Row = 0; Row < Rows; ++Row)
        {
            // Bottom sample sits at the top of a climbable step, top sample at
            // the crown of the head — the band a body actually occupies.
            const float RowT = (Rows == 1) ? 0.5f : (float)Row / (float)(Rows - 1);
            const float ZLow = StepUpCm;
            const float ZHigh = HalfHeight * 2.0f - 10.0f;
            const FVector RowOffset = Up * (ZLow + (ZHigh - ZLow) * RowT - HalfHeight);

            const FVector RayStart = Base + ColOffset + RowOffset;
            const FVector RayEnd = RayStart + Forward * (float)DistanceCm;

            FHitResult RayHit;
            const bool bRayBlocked = World->LineTraceSingleByChannel(
                RayHit, RayStart, RayEnd, ECC_Pawn, QueryParams);

            TSharedPtr<FJsonObject> Cell = MakeShared<FJsonObject>();
            Cell->SetStringField(TEXT("column"), ColumnLabel(Col));
            Cell->SetStringField(TEXT("row"), RowLabel(Row));
            Cell->SetBoolField(TEXT("blocked"), bRayBlocked);
            if (bRayBlocked)
            {
                ++BlockedCells;
                NearestCm = FMath::Min(NearestCm, RayHit.Distance);
                FillHitIdentity(RayHit, Cell);
            }
            else
            {
                bColumnOpen = true;
            }
            CellRows.Add(MakeShared<FJsonValueObject>(Cell));
        }

        if (bColumnOpen) OpenColumns.Add(MakeShared<FJsonValueString>(ColumnLabel(Col)));
        else             BlockedColumns.Add(MakeShared<FJsonValueString>(ColumnLabel(Col)));
    }

    for (int32 Row = 0; Row < Rows; ++Row)
    {
        bool bRowOpen = false;
        for (int32 Col = 0; Col < Columns; ++Col)
        {
            const TSharedPtr<FJsonObject>* Cell;
            if (CellRows[Col * Rows + Row]->TryGetObject(Cell))
            {
                bool bBlocked = true;
                (*Cell)->TryGetBoolField(TEXT("blocked"), bBlocked);
                if (!bBlocked) { bRowOpen = true; break; }
            }
        }
        if (bRowOpen) OpenRows.Add(MakeShared<FJsonValueString>(RowLabel(Row)));
    }

    Result->SetArrayField(TEXT("open_columns"), OpenColumns);
    Result->SetArrayField(TEXT("blocked_columns"), BlockedColumns);
    Result->SetArrayField(TEXT("open_rows"), OpenRows);
    Result->SetArrayField(TEXT("cells"), CellRows);
    Result->SetNumberField(TEXT("blocked_fraction"),
                           TotalCells > 0 ? (double)BlockedCells / (double)TotalCells : 0.0);
    Result->SetNumberField(TEXT("nearest_cm"), (double)NearestCm);
    // "Completely blocked" is the raster's verdict, not the sweep's: the sweep can
    // clip one shoulder while a real gap remains.
    Result->SetBoolField(TEXT("fully_blocked"), BlockedCells == TotalCells);
    Result->SetBoolField(TEXT("hit"), bSweepBlocked || BlockedCells > 0);

    return Result;
}

// ---------------------------------------------------------------------------
// #92 — the radar. The same capsule sweep as above, fired all the way round the
// compass in ONE round trip.
//
// The handler above answers "what is in front of me". That is the only spatial
// question this runtime could ask, and it is the reason APCs get trapped: in
// SR51 the log said "open headings: none — boxed in" three times, and each of
// those meant "none of the four headings in front of my face". Nobody had ever
// measured behind him. The way out was there every time.
//
// Python can already do this by calling get_character_forward_volume once per
// heading, and that is exactly how it shipped first — correct, and eight socket
// round trips per agent per tick on a bridge that opens a fresh connection per
// command.
//
// Everything costly about the volume probe is the 5x3 raster, and a radar does
// not want it: "how far until something stops me that way" is the capsule sweep
// on its own. So the whole ring costs less than the four raster probes it
// replaces, while measuring twice as many headings, on every tick instead of
// only after a collision.
// ---------------------------------------------------------------------------

// #101 — walkable ground is a measurement, not an assumption. The radar above
// measures AIR: SR56 stood Dufus on a raised slab and in a carport floor with
// a hole, and both times the ring reported room to travel because the air
// really was clear — nothing had ever asked whether the ground under a point
// is ground the body can walk FROM. UNavigationSystemV1::ProjectPointToNavigation
// is that question, and it is the same test the move commands already route
// on, so this is the body reading its own sense, not inventing a new one.
// The word "navmesh" stops here — every JSON field and every log line below
// says "walkable ground" or "ground", because that is the only vocabulary
// that is allowed to reach Python or the prompt ([[architecture_lizard_brain_sensing]]).
static bool ProjectToWalkableGround(UNavigationSystemV1* NavSys, const FVector& Point,
                                    const FVector& Extent, FVector& OutGround)
{
    if (!NavSys) return false;
    FNavLocation NavLoc;
    if (!NavSys->ProjectPointToNavigation(Point, NavLoc, Extent)) return false;
    OutGround = NavLoc.Location;
    return true;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleGetCharacterRadar(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UWorld* World = Actor->GetWorld();
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No world"));

    double DistanceCm = 2000.0;
    Params->TryGetNumberField(TEXT("distance_cm"), DistanceCm);

    // Sectors are spread evenly over the full turn. 8 is the compass the APC
    // steers with; more is allowed so the ring can be made finer without a
    // second command.
    int32 Sectors = 8;
    { int32 V = 0; if (Params->TryGetNumberField(TEXT("sectors"), V) && V >= 4 && V <= 36) Sectors = V; }

    // The ring may be rotated off the body's facing, so the caller can align
    // sector 0 with a WORLD heading. Python wants compass words, and a purely
    // body-relative ring would rename every sector the moment the body turned.
    double YawOffsetDeg = 0.0;
    Params->TryGetNumberField(TEXT("yaw_offset_deg"), YawOffsetDeg);

    // Read the real capsule rather than hard-coding a body size.
    float Radius = 34.0f;
    float HalfHeight = 88.0f;
    bool bCapsuleFromEngine = false;
    if (ACharacter* AsCharacter = Cast<ACharacter>(Actor))
    {
        if (UCapsuleComponent* Capsule = AsCharacter->GetCapsuleComponent())
        {
            Radius = Capsule->GetScaledCapsuleRadius();
            HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
            bCapsuleFromEngine = true;
        }
    }

    float StepUpCm = 45.0f;
    if (ACharacter* AsCharacter = Cast<ACharacter>(Actor))
    {
        if (UCharacterMovementComponent* Move = AsCharacter->GetCharacterMovement())
        {
            StepUpCm = Move->MaxStepHeight;
        }
    }

    // Same lift-and-shorten as the forward volume: a sweep at full body height
    // calls every kerb a wall, and a radar that does that reports a pavement
    // edge as an enclosing ring.
    const float SweepHalfHeight = FMath::Max(HalfHeight - StepUpCm * 0.5f, Radius + 1.0f);
    const FVector Base  = Actor->GetActorLocation();
    const FVector Start = Base + FVector::UpVector * (StepUpCm * 0.5f);

    FCollisionQueryParams QueryParams(TEXT("Radar"), /*bTraceComplex=*/false, Actor);
    QueryParams.bReturnPhysicalMaterial = true;

    // #101: the actor location is the capsule CENTRE, HalfHeight above the
    // soles. Every ground projection below starts at the feet — a 60 cm reach
    // from the centre would miss the very floor the body stands on.
    const FVector Feet = Base - FVector::UpVector * HalfHeight;
    // #101: the ground sense reads whatever nav system this world has, if any.
    // A world with none simply gets no ground_cm/ground_under_feet/nearest_ground
    // fields — silence, not a false "not walkable", is the honest answer when
    // nothing was measured (rule 12).
    UNavigationSystemV1* NavSys = UNavigationSystemV1::GetCurrent(World);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("distance_cm"), DistanceCm);
    Result->SetNumberField(TEXT("sectors"), Sectors);
    Result->SetNumberField(TEXT("body_radius_cm"), (double)Radius);
    Result->SetBoolField(TEXT("capsule_from_engine"), bCapsuleFromEngine);
    Result->SetNumberField(TEXT("step_up_cm"), (double)StepUpCm);
    Result->SetNumberField(TEXT("facing_yaw"), (double)Actor->GetActorRotation().Yaw);

    if (NavSys)
    {
        // "Standing where no walk can start" (SR56) is invisible to a probe that
        // only ever looks outward, so this is the one measurement taken AT the
        // body rather than away from it.
        FVector UnderFeet;
        const bool bGroundedHere = ProjectToWalkableGround(
            NavSys, Feet, FVector(30.0f, 30.0f, StepUpCm + 30.0f), UnderFeet);
        Result->SetBoolField(TEXT("ground_under_feet"), bGroundedHere);
        if (!bGroundedHere)
        {
            FVector NearestGround;
            if (ProjectToWalkableGround(NavSys, Feet, FVector(400.0f, 400.0f, 400.0f), NearestGround))
            {
                const FVector ToGround = NearestGround - Feet;
                TSharedPtr<FJsonObject> Nearest = MakeVec3Field(NearestGround);
                Nearest->SetNumberField(TEXT("distance_cm"), (double)ToGround.Size());
                Nearest->SetNumberField(TEXT("world_yaw"), (double)ToGround.Rotation().Yaw);
                Result->SetObjectField(TEXT("nearest_ground"), Nearest);
            }
            // No entry within 400 cm either — nearest_ground is simply absent,
            // which the caller must read as "not measured", never as "none".
        }
    }

    TArray<TSharedPtr<FJsonValue>> Ring;
    const double Span = 360.0 / (double)Sectors;
    const float GroundStepCm = 50.0f;
    const float GroundExtentZ = StepUpCm + 60.0f;
    for (int32 i = 0; i < Sectors; ++i)
    {
        const double Offset = YawOffsetDeg + Span * (double)i;
        const FRotator ProbeRotation = Actor->GetActorRotation() + FRotator(0.0f, (float)Offset, 0.0f);
        const FVector Forward = ProbeRotation.Vector().GetSafeNormal();
        const FVector End = Start + Forward * (float)DistanceCm;

        FHitResult SweepHit;
        const bool bBlocked = World->SweepSingleByChannel(
            SweepHit, Start, End, ProbeRotation.Quaternion(), ECC_Pawn,
            FCollisionShape::MakeCapsule(Radius, SweepHalfHeight), QueryParams);

        TSharedPtr<FJsonObject> Sector = MakeShared<FJsonObject>();
        Sector->SetNumberField(TEXT("yaw_offset_deg"), Offset);
        Sector->SetNumberField(TEXT("world_yaw"), (double)ProbeRotation.Yaw);
        Sector->SetBoolField(TEXT("fits"), !bBlocked);
        // Distance to first contact, or the full reach when nothing was struck —
        // the same meaning "clearance_cm" carries on the forward volume.
        Sector->SetNumberField(TEXT("clearance_cm"),
                               bBlocked ? (double)SweepHit.Distance : DistanceCm);
        if (bBlocked)
        {
            TSharedPtr<FJsonObject> Contact = MakeShared<FJsonObject>();
            FillHitIdentity(SweepHit, Contact);
            Sector->SetObjectField(TEXT("contact"), Contact);
        }

        // #101: the ground column. Air is not permission to walk (a lesson
        // #94 already taught memory) and this is the same lesson taught to the
        // radar itself — walk this heading outward every 50 cm until a sample
        // no longer projects onto walkable ground, and that is where the
        // ground, not the air, ends.
        if (NavSys)
        {
            double GroundEndCm = DistanceCm;
            for (float D = GroundStepCm; D <= (float)DistanceCm; D += GroundStepCm)
            {
                FVector Sample = Feet + Forward * D;
                FVector Ignored;
                if (!ProjectToWalkableGround(
                        NavSys, Sample, FVector(30.0f, 30.0f, GroundExtentZ), Ignored))
                {
                    GroundEndCm = (double)D;
                    break;
                }
            }
            Sector->SetNumberField(TEXT("ground_cm"), GroundEndCm);
        }

        Ring.Add(MakeShared<FJsonValueObject>(Sector));
    }
    Result->SetArrayField(TEXT("ring"), Ring);

    return Result;
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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
        Result->SetStringField(TEXT("warning"), TEXT("No APCCharacterComponent on actor — attach one to enable full status"));
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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
    UGameplayStatics::GetAllActorsOfClass(FUnrealMCPCommonUtils::GetGameWorld(), ACharacter::StaticClass(), AllActors);

    TArray<TSharedPtr<FJsonValue>> Nearby;
    for (AActor* Other : AllActors)
    {
        if (!Other || Other == Actor) continue;
        float Dist = FVector::Dist(Origin, Other->GetActorLocation());
        if (Dist <= static_cast<float>(Radius))
        {
            TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
            Entry->SetStringField(TEXT("name"), Other->GetName());
            Entry->SetStringField(TEXT("label"), Other->GetActorLabel());
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

// #101 — SR56: this handler used to call SimpleMoveToLocation and report
// success without ever asking whether a path exists. Both SR56 traps (Dufus
// on a raised slab, Dufus in a carport floor with a hole under him) are
// exactly this: the order was accepted, the AI state said "moving", and the
// body advanced 0-15 cm across twelve ticks and ~100 s because there was
// nothing to walk on FROM where it stood. `FindPathToLocationSynchronously`
// is the same pathfinder the move itself would use, asked first instead of
// discovered by watching the body fail to arrive. `success` stays true —
// the path test is the answer, not a reason to fail the call.
TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandMoveTo(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    ACharacter* Character = Cast<ACharacter>(Actor);
    if (!Character) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor is not a Character: %s"), *Actor->GetName()));

    AController* Controller = Character->GetController();
    if (!Controller) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Character has no Controller — ensure an AIController is assigned"));

    UWorld* World = Actor->GetWorld();
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No world"));

    FVector Destination = FVector::ZeroVector;
    AActor* TargetActor = nullptr;   // set only for the target_actor form, so a valid path still tracks a moving target

    if (Params->HasField(TEXT("location")))
    {
        Destination = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    else if (Params->HasField(TEXT("target_actor")))
    {
        FString TargetName;
        Params->TryGetStringField(TEXT("target_actor"), TargetName);
        TargetActor = FindActorByName(TargetName);
        if (!TargetActor) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Target actor not found: %s"), *TargetName));
        Destination = TargetActor->GetActorLocation();
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Provide 'location' [x,y,z] or 'target_actor' name"));
    }

    const FVector StartLoc = Actor->GetActorLocation();
    FString PathKind = TEXT("none");
    double PathLengthCm = 0.0;
    FVector PathEnd = StartLoc;   // "none" leaves the answer at the body — it never left

    if (UNavigationPath* NavPath = UNavigationSystemV1::FindPathToLocationSynchronously(
            World, StartLoc, Destination, Actor))
    {
        if (NavPath->IsValid() && NavPath->PathPoints.Num() > 0)
        {
            PathKind = NavPath->IsPartial() ? TEXT("partial") : TEXT("full");
            PathLengthCm = NavPath->GetPathLength();
            PathEnd = NavPath->PathPoints.Last();
        }
    }
    const double PathEndGapCm = FVector::Dist(PathEnd, Destination);

    const bool bMoved = PathKind != TEXT("none");
    if (bMoved)
    {
        if (TargetActor)
            UAIBlueprintHelperLibrary::SimpleMoveToActor(Controller, TargetActor);
        else
            UAIBlueprintHelperLibrary::SimpleMoveToLocation(Controller, Destination);

        UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
        if (Comp)
        {
            Comp->AIState = TEXT("moving");
            Comp->CurrentAction = FString::Printf(TEXT("moving_to [%.0f, %.0f, %.0f]"), Destination.X, Destination.Y, Destination.Z);
        }
    }
    else
    {
        // Nothing to walk (#101) — no move is issued. This is the fact SR56
        // needed on tick 1 instead of a hundred seconds of standing still.
        UE_LOG(LogTemp, Warning,
            TEXT("[UnrealMCP] %s: no path to (%.0f, %.0f, %.0f) from (%.0f, %.0f, %.0f) — move not issued"),
            *Actor->GetName(), Destination.X, Destination.Y, Destination.Z,
            StartLoc.X, StartLoc.Y, StartLoc.Z);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("destination"), MakeVec3Field(Destination));
    Result->SetBoolField(TEXT("moved"), bMoved);
    Result->SetStringField(TEXT("path"), PathKind);
    Result->SetNumberField(TEXT("path_length_cm"), PathLengthCm);
    Result->SetObjectField(TEXT("path_end"), MakeVec3Field(PathEnd));
    Result->SetNumberField(TEXT("path_end_gap_cm"), PathEndGapCm);
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (Comp)
    {
        Comp->AIState = TEXT("idle");
        Comp->CurrentAction = TEXT("stopped");
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandTeleport(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    if (!Params->HasField(TEXT("location")))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'location' parameter ([x, y, z])"));

    FVector Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    FRotator Rotation = Actor->GetActorRotation();
    if (Params->HasField(TEXT("rotation")))
        Rotation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"));

    // Cancel any in-flight nav move so the AI doesn't resume its old path after the jump.
    if (ACharacter* Character = Cast<ACharacter>(Actor))
    {
        if (AAIController* AIController = Cast<AAIController>(Character->GetController()))
            AIController->StopMovement();
        if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
            Movement->StopMovementImmediately();
    }

    if (!Actor->TeleportTo(Location, Rotation, false, true))
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("TeleportTo failed for: %s"), *Actor->GetName()));

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (Comp)
    {
        Comp->AIState = TEXT("idle");
        Comp->CurrentAction = TEXT("teleported");
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("location"), MakeVec3Field(Actor->GetActorLocation()));
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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
        bool bMatches = !bDropSpecific;
        if (bDropSpecific && Attached_Actor)
        {
            bMatches = Attached_Actor->GetName() == ItemName;
#if WITH_EDITOR
            if (!bMatches)
            {
                bMatches = Attached_Actor->GetActorLabel().Equals(ItemName, ESearchCase::IgnoreCase);
            }
#endif
        }
        if (bMatches)
        {
            Attached_Actor->DetachFromActor(DetachRules);
            Dropped.Add(Attached_Actor->GetName());
        }
    }

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

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

    UAPCCharacterComponent* Comp = GetAPCComponent(Actor);
    if (!Comp) return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("No APCCharacterComponent on: %s"), *Actor->GetName()));

    Comp->AIState = NewState;
    Comp->OnAIStateChanged(NewState);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("ai_state"), NewState);
    return Result;
}

// ---------------------------------------------------------------------------
// #101 — the footing reflex. SR56's carport hole and raised slab are both
// cases where the body stood somewhere ProjectPointToNavigation cannot walk
// FROM — the radar's ground_under_feet is what discovers it. This is the
// primitive that does something about it: a real body steps down off a slab
// or out of a hole onto the nearest ground it can actually reach, it does not
// get rescued from across the map. Anything past 400 cm is left alone —
// that is not a footing correction, that is a teleport, and the fact goes
// back to Python instead so the model can decide.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FUnrealMCPCharacterCommands::HandleCommandStepToGround(const TSharedPtr<FJsonObject>& Params)
{
    FString Error;
    AActor* Actor = ResolveCharacter(Params, Error);
    if (!Actor) return FUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UWorld* World = Actor->GetWorld();
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No world"));

    UNavigationSystemV1* NavSys = UNavigationSystemV1::GetCurrent(World);
    if (!NavSys) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No navigation system in this world"));

    const FVector From = Actor->GetActorLocation();

    // Actor location is the capsule centre; project from the soles — the same
    // origin the radar's ground_under_feet used to raise this reflex.
    float HalfHeight = 88.0f;
    float StepUpCm = 45.0f;
    if (ACharacter* AsCharacter = Cast<ACharacter>(Actor))
    {
        if (UCapsuleComponent* Capsule = AsCharacter->GetCapsuleComponent())
            HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
        if (UCharacterMovementComponent* Move = AsCharacter->GetCharacterMovement())
            StepUpCm = Move->MaxStepHeight;
    }
    const FVector Feet = From - FVector::UpVector * HalfHeight;

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetObjectField(TEXT("from"), MakeVec3Field(From));

    FVector UnderFeet;
    if (ProjectToWalkableGround(NavSys, Feet, FVector(30.0f, 30.0f, StepUpCm + 30.0f), UnderFeet))
    {
        Result->SetBoolField(TEXT("stepped"), false);
        Result->SetStringField(TEXT("reason"), TEXT("already on walkable ground"));
        return Result;
    }

    FVector NearestGround;
    if (!ProjectToWalkableGround(NavSys, Feet, FVector(400.0f, 400.0f, 400.0f), NearestGround))
    {
        Result->SetBoolField(TEXT("stepped"), false);
        Result->SetStringField(TEXT("reason"), TEXT("no walkable ground within 400 cm"));
        return Result;
    }

    const double DistanceCm = FVector::Dist(Feet, NearestGround);
    if (DistanceCm > 400.0)
    {
        Result->SetBoolField(TEXT("stepped"), false);
        Result->SetNumberField(TEXT("distance_cm"), DistanceCm);
        Result->SetStringField(TEXT("reason"), FString::Printf(
            TEXT("nearest walkable ground is %.0f cm away — beyond the 400 cm step"), DistanceCm));
        return Result;
    }

    // Keep the body's own height above the ground point rather than dropping
    // it to the nav mesh surface itself — the capsule stands ON the ground,
    // it does not sink into it.
    const FVector StepTarget = NearestGround + FVector::UpVector * HalfHeight;

    // Cancel any in-flight move first, same reasoning as HandleCommandTeleport —
    // an AI controller must not resume a stale path from the spot just left.
    if (ACharacter* Character = Cast<ACharacter>(Actor))
    {
        if (AAIController* AIController = Cast<AAIController>(Character->GetController()))
            AIController->StopMovement();
        if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
            Movement->StopMovementImmediately();
    }

    if (!Actor->TeleportTo(StepTarget, Actor->GetActorRotation(), false, true))
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("TeleportTo failed stepping to ground for: %s"), *Actor->GetName()));

    const FVector Landed = Actor->GetActorLocation();
    UE_LOG(LogTemp, Warning,
        TEXT("[UnrealMCP] %s footing: stepped %.1f cm from (%.0f, %.0f, %.0f) onto walkable ground at (%.0f, %.0f, %.0f)"),
        *Actor->GetName(), DistanceCm, From.X, From.Y, From.Z, Landed.X, Landed.Y, Landed.Z);

    Result->SetBoolField(TEXT("stepped"), true);
    Result->SetObjectField(TEXT("to"), MakeVec3Field(Landed));
    Result->SetNumberField(TEXT("distance_cm"), DistanceCm);
    return Result;
}
