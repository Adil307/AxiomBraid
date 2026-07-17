$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "AxiomBraid 2.0.0 — Doxygen Documentation" -ForegroundColor Cyan

if (-not (Get-Command doxygen -ErrorAction SilentlyContinue)) {
    throw "Doxygen was not found on PATH. Install it with: winget install --id DimitriVanHeesch.Doxygen -e"
}

if (-not (Test-Path "src\axiombraid")) {
    throw "src\axiombraid was not found. Run this script from the AxiomBraid project root."
}

New-Item -ItemType Directory -Force "docs\doxygen" | Out-Null
& doxygen .\Doxyfile

$index = Join-Path (Get-Location) "docs\doxygen\html\index.html"
if (-not (Test-Path $index)) {
    throw "The expected Doxygen index was not generated: $index"
}

Write-Host "Documentation generated successfully:" -ForegroundColor Green
Write-Host $index -ForegroundColor Green
Start-Process $index
