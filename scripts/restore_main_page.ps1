# Restore main page files from the last committed version (git HEAD).
# Run from project root: .\scripts\restore_main_page.ps1
# Or from any dir: & "D:\LearnCentreWebsite\scripts\restore_main_page.ps1"

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { $PWD }
if (-not (Test-Path (Join-Path $root ".git"))) {
    $root = $PWD
}
Set-Location $root

$files = @(
    "WebSite/static/css/main_pages.css",
    "WebSite/static/js/main_pages.js",
    "WebSite/templates/main_pages/base.html",
    "WebSiteFront/templates/Main_page/lastFigma versuin.html"
)

foreach ($f in $files) {
    $path = Join-Path $root $f
    if (Test-Path $path) {
        git checkout HEAD -- $f
        Write-Host "Restored: $f"
    } else {
        git checkout HEAD -- $f 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Host "Restored: $f" } else { Write-Host "Skip (not in repo): $f" }
    }
}
Write-Host "Done. Main page files restored from git."
