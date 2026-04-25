// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Camera/CameraActor.h"
#include "Components/SceneCaptureComponent2D.h"

//Always last
#include "CameraCaptureActor.generated.h"


UCLASS()
class UNREALMCP_API ACameraCaptureActor : public ACameraActor
{
	GENERATED_BODY()

public:
	// Sets default values for this actor's properties
	ACameraCaptureActor();

protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

public:
	// Called every frame
	virtual void Tick(float DeltaTime) override;
	virtual void PostInitializeComponents() override;
	UPROPERTY()
	USceneCaptureComponent2D* capture_component;
	UPROPERTY()
	UTextureRenderTarget2D* render_target;

	UFUNCTION(BlueprintCallable, Category = "CameraCaptureActor")
	void SaveCameraImageToFile(const FString& FileName);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "CameraCaptureActor")
	bool bBeAFooy;

private:
	UTextureRenderTarget2D* CreateRenderTarget(int32 Width, int32 Height);
	void SetupSceneCaptureComponent(ACameraActor* CameraActor, UTextureRenderTarget2D* RenderTarget);
	void SaveCameraToFile(UTextureRenderTarget2D* RenderTarget, const FString& FilePath);
	void CaptureCameraViewToFile(ACameraActor* CameraActor, const FString& FilePath);

};
