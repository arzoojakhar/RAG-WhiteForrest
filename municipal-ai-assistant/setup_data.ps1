# setup_data.ps1
# Copies hackathon documents into the correct data directories.
# Run from: d:\BlackForestHackathon\
# Usage: .\setup_data.ps1

$root      = $PSScriptRoot
$hackathon = Split-Path $root -Parent

$kb     = Join-Path $root "backend\data\knowledge_base"
$extra  = Join-Path $root "backend\data\additional_documents"
$tmpl   = Join-Path $root "backend\data\templates"

Write-Host "Copying knowledge base documents..."
$kbSrc = Join-Path $hackathon "01_Knowledge_Base-20260508T225647Z-3-001\01_Knowledge_Base"
Get-ChildItem $kbSrc -File | Where-Object { $_.Extension -in ".PDF",".pdf",".docx",".xlsx" } | ForEach-Object {
    Copy-Item $_.FullName -Destination $kb -Force
    Write-Host "  + $($_.Name)"
}

Write-Host "Copying additional documents..."
$extraSrc = Join-Path $hackathon "02_Additional_Sample_Documents-20260508T225653Z-3-001\02_Additional_Sample_Documents"
Get-ChildItem $extraSrc -File | Where-Object { $_.Extension -in ".PDF",".pdf",".docx",".xlsx" } | ForEach-Object {
    Copy-Item $_.FullName -Destination $extra -Force
    Write-Host "  + $($_.Name)"
}

Write-Host "Copying templates..."
$tmplSrc = Join-Path $hackathon "03_Templates_Shared-20260508T225656Z-3-001\03_Templates_Shared"
Get-ChildItem $tmplSrc -File | ForEach-Object {
    Copy-Item $_.FullName -Destination $tmpl -Force
    Write-Host "  + $($_.Name)"
}

Write-Host ""
Write-Host "Done! Now start the backend (it will auto-index on startup):"
Write-Host "  cd municipal-ai-assistant\backend"
Write-Host "  python -m venv .venv"
Write-Host "  .venv\Scripts\activate"
Write-Host "  pip install -r requirements.txt"
Write-Host "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
