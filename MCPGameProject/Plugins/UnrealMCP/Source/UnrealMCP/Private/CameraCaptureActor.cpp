// Fill out your copyright notice in the Description page of Project Settings.


#include "CameraCaptureActor.h"
#include "Camera/CameraComponent.h"
#include "SceneInterface.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Modules/ModuleManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "ImageUtils.h"


//--------------------------------------------------------------------------------------------------------------------------------------
// Sets default values
ACameraCaptureActor::ACameraCaptureActor()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

}
//--------------------------------------------------------------------------------------------------------------------------------------
void ACameraCaptureActor::PostInitializeComponents()
{
    Super::PostInitializeComponents();

    AActor* actor = this;
    TArray<USceneComponent*> ChildComponents;



}
//--------------------------------------------------------------------------------------------------------------------------------------
// Called when the game starts or when spawned
void ACameraCaptureActor::BeginPlay()
{
	Super::BeginPlay();

    bBeAFooy = true;



}
//--------------------------------------------------------------------------------------------------------------------------------------
// Called every frame
void ACameraCaptureActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

    /*

    if (bBeAFooy)
    {
        UE_LOG(LogTemp, Log, TEXT("bBeAFooy = true"));
        ACameraActor* MyCameraActor = this; // ... // Obtain your CameraActor somehow
        FString FilePath = TEXT("CapturedCameraView.png");
        CaptureCameraViewToFile(MyCameraActor, FilePath);
        bBeAFooy = false;

    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("bBeAFooy = false"));

    }

    */

}
//--------------------------------------------------------------------------------------------------------------------------------------
// Called by BP
void ACameraCaptureActor::SaveCameraImageToFile(const FString& FileName)
{
    ACameraActor* MyCameraActor = this;
    CaptureCameraViewToFile(MyCameraActor, FileName);

}
//--------------------------------------------------------------------------------------------------------------------------------------
UTextureRenderTarget2D* ACameraCaptureActor::CreateRenderTarget(int32 Width, int32 Height)
{
    UTextureRenderTarget2D* RenderTarget = NewObject<UTextureRenderTarget2D>();
    RenderTarget->InitAutoFormat(Width, Height);
    RenderTarget->ClearColor = FLinearColor::Black;
    RenderTarget->UpdateResourceImmediate(true);
    return RenderTarget;
}
//--------------------------------------------------------------------------------------------------------------------------------------
void ACameraCaptureActor::SetupSceneCaptureComponent(ACameraActor* CameraActor, UTextureRenderTarget2D* RenderTarget)
{
    if (CameraActor && RenderTarget)
    {
        USceneCaptureComponent2D* SceneCaptureComponent = NewObject<USceneCaptureComponent2D>(CameraActor);

        SceneCaptureComponent->bCaptureEveryFrame = false;
        SceneCaptureComponent->bCaptureOnMovement = false;

        SceneCaptureComponent->SetupAttachment(CameraActor->GetRootComponent());
        SceneCaptureComponent->SetRelativeLocation(FVector::ZeroVector);
        SceneCaptureComponent->TextureTarget = RenderTarget;
        SceneCaptureComponent->CaptureSource = SCS_FinalColorLDR;

        SceneCaptureComponent->RegisterComponentWithWorld(CameraActor->GetWorld());

        // Update the scene capture immediately
        SceneCaptureComponent->CaptureScene();
    }
}
//--------------------------------------------------------------------------------------------------------------------------------------
void ACameraCaptureActor::SaveCameraToFile(UTextureRenderTarget2D* RenderTarget, const FString& FilePath)
{
    if (!RenderTarget)
    {
        UE_LOG(LogTemp, Error, TEXT("RenderTarget is null."));
        return;
    }

    FRenderTarget* RenderTargetResource = RenderTarget->GameThread_GetRenderTargetResource();
    int32 Width = RenderTarget->SizeX;
    int32 Height = RenderTarget->SizeY;

    TArray<FColor> Bitmap;
    RenderTargetResource->ReadPixels(Bitmap);

    TArray<uint8> CompressedBitmap;
    FImageUtils::CompressImageArray(Width, Height, Bitmap, CompressedBitmap);

    FString AbsoluteFilePath = FPaths::ProjectDir() + FilePath;
    if (FFileHelper::SaveArrayToFile(CompressedBitmap, *AbsoluteFilePath))
    {
        UE_LOG(LogTemp, Log, TEXT("Successfully saved render target to %s"), *AbsoluteFilePath);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to save render target to %s"), *AbsoluteFilePath);
    }
}
//--------------------------------------------------------------------------------------------------------------------------------------
void ACameraCaptureActor::CaptureCameraViewToFile(ACameraActor* CameraActor, const FString& FilePath)
{
    if (!CameraActor)
    {
        UE_LOG(LogTemp, Error, TEXT("CameraActor is null."));
        return;
    }

    int32 Width = 1920;
    int32 Height = 1080;

    UTextureRenderTarget2D* RenderTarget = CreateRenderTarget(Width, Height);
    SetupSceneCaptureComponent(CameraActor, RenderTarget);

    SaveCameraToFile(RenderTarget, FilePath);
}
