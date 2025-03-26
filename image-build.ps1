param(
    [Parameter(Position=0)]
    [string]$Version = "latest"
)

# Define the images to build
$IMAGES = @(
    @{
        Name = "mayafit/alfred-devops-service"  # Changed format
        Path = "."
        File = "Dockerfile"
    },
    @{
        Name = "mayafit/alfred-ci-agent"        # Changed format
        Path = "./agents/ci_agent"
        File = "Dockerfile"
    },
    @{
        Name = "mayafit/alfred-helm-agent"      # Changed format
        Path = "./agents/helm_agent"
        File = "Dockerfile"
    },
    @{
        Name = "mayafit/alfred-deploy-agent"    # Changed format
        Path = "./agents/deploy_agent"
        File = "Dockerfile"
    }
)

# Function to build an image
function Build-DockerImage {
    param (
        [string]$Name,
        [string]$Path,
        [string]$File,
        [string]$Version
    )
    
    Write-Host "Building $Name`:$Version..." -ForegroundColor Cyan
    
    docker build -t "$Name`:$Version" -f "$Path/$File" $Path
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully built $Name`:$Version" -ForegroundColor Green
    } else {
        Write-Host "Failed to build $Name`:$Version" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Building images with version: $Version" -ForegroundColor Yellow

# Build all images
foreach ($image in $IMAGES) {
    Build-DockerImage -Name $image.Name -Path $image.Path -File $image.File -Version $Version
}

Write-Host "`nAll images built successfully!" -ForegroundColor Green