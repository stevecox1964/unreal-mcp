#include "APCCharacterComponent.h"

UAPCCharacterComponent::UAPCCharacterComponent()
{
    PrimaryComponentTick.bCanEverTick = false;

    AIState = TEXT("idle");
    CurrentAction = TEXT("none");
    Health = 100.0f;
}
