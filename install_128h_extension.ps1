param()

$ErrorActionPreference = "Stop"

$Source = Join-Path $PSScriptRoot "premiere_extension\STT-Audio-Bridge"
$DestinationRoot = Join-Path $env:APPDATA "Adobe\CEP\extensions"
$Destination = Join-Path $DestinationRoot "STT-Audio-Bridge"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Extension source not found: $Source"
}

New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null

if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
}

Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force

foreach ($Version in 9..15) {
    $RegistryPath = "HKCU:\Software\Adobe\CSXS.$Version"
    New-Item -Path $RegistryPath -Force | Out-Null
    New-ItemProperty `
        -Path $RegistryPath `
        -Name "PlayerDebugMode" `
        -Value "1" `
        -PropertyType String `
        -Force | Out-Null
}

Write-Host ""
Write-Host "STT Audio Bridge installed successfully." -ForegroundColor Green
Write-Host "Installed to: $Destination"
Write-Host ""
Write-Host "Close Premiere completely, then open it again." -ForegroundColor Yellow
Write-Host "Open: Window > Extensions (Legacy) > STT Audio Bridge"
