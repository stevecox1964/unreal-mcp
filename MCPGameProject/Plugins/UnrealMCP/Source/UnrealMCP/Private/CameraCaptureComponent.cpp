// Fill out your copyright notice in the Description page of Project Settings.


#include "CameraCaptureComponent.h"

// Sets default values for this component's properties
UCameraCaptureComponent::UCameraCaptureComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}


// Called when the game starts
void UCameraCaptureComponent::BeginPlay()
{
	Super::BeginPlay();
}


// Called every frame
void UCameraCaptureComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}
