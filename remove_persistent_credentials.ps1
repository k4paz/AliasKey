# ============================================================================
# HME - Remove Persistent Credentials
# ============================================================================
# This script removes all Apple HME environment variables from your user
# account that were saved by hme_setup.exe
#
# Usage:
#   .\remove_persistent_credentials.ps1
#
# This will delete variables from:
#   HKEY_CURRENT_USER\Environment (Windows Registry)
#
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  HME - Remove Persistent Credentials" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will PERMANENTLY REMOVE all Apple HME credentials from your user account." -ForegroundColor Yellow
Write-Host ""

# Ask for confirmation
$confirmation = Read-Host "Continue? [Y/N]"
if ($confirmation -ne 'Y' -and $confirmation -ne 'y') {
    Write-Host ""
    Write-Host "Cancelled." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "Removing persistent environment variables..." -ForegroundColor Cyan
Write-Host ""

# Function to remove persistent user environment variable
function Remove-PersistentEnvVar {
    param(
        [string]$Name
    )
    
    try {
        # Remove from registry
        [System.Environment]::SetEnvironmentVariable($Name, $null, [System.EnvironmentVariableTarget]::User)
        
        # Also remove from current session
        if (Test-Path "env:$Name") {
            Remove-Item -Path "env:$Name" -ErrorAction SilentlyContinue
        }
        
        Write-Host "  [OK] Removed $Name" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "  [WARN] Failed to remove $Name : $_" -ForegroundColor Yellow
        return $false
    }
}

# List of all variables to remove
$variables = @(
    "APPLE_DSID",
    "APPLE_CLIENT_ID",
    "APPLE_GROUP",
    "APPLE_CLIENT_BUILD",
    "APPLE_CLIENT_MASTERING",
    "APPLE_WEBAUTH_USER",
    "APPLE_WEB_KB",
    "APPLE_HSA_TRUST",
    "APPLE_DS_WEB_SESSION_TOKEN",
    "APPLE_WEB_ID",
    "APPLE_WEBAUTH_VALIDATE",
    "APPLE_WEBAUTH_TOKEN",
    "APPLE_PCS_EVENTS",
    "APPLE_PCS_DOCUMENTS",
    "APPLE_PCS_PHOTOS",
    "APPLE_PCS_CLOUDKIT",
    "APPLE_PCS_SAFARI",
    "APPLE_PCS_MAIL",
    "APPLE_PCS_NOTES",
    "APPLE_PCS_NEWS",
    "APPLE_PCS_SHARING"
)

$removed = 0
$notFound = 0

foreach ($var in $variables) {
    if (Remove-PersistentEnvVar $var) {
        $removed++
    } else {
        $notFound++
    }
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Cleanup Complete!" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[SUCCESS] Removed $removed environment variables" -ForegroundColor Green

if ($notFound -gt 0) {
    Write-Host "[INFO] $notFound variables were not found (may have been already removed)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Credentials have been removed from:" -ForegroundColor Gray
Write-Host "  HKEY_CURRENT_USER\Environment" -ForegroundColor Gray
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "  - Close and reopen any terminals for changes to take full effect" -ForegroundColor White
Write-Host "  - Variables are removed from THIS session immediately" -ForegroundColor White
Write-Host "  - The executable will no longer work until credentials are set again" -ForegroundColor White
Write-Host ""
Write-Host "To set credentials again, run dist\hme_setup.exe." -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
