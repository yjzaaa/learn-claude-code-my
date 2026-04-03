# Project Cleanup Script
# Run: PowerShell -ExecutionPolicy Bypass -File cleanup-project.ps1

param(
    [switch]$DryRun,
    [switch]$Force
)

$itemsToRemove = @()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       Project Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. .next build cache
if (Test-Path "web/.next") {
    $size = (Get-ChildItem web/.next -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $itemsToRemove += @{Path="web/.next"; Desc="Next.js build cache"; Size=$size}
}

# 2. Python cache
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $itemsToRemove += @{Path=$_.FullName; Desc="Python cache"; Size=$size}
}

# 3. Pytest cache
if (Test-Path ".pytest_cache") {
    $size = (Get-ChildItem .pytest_cache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $itemsToRemove += @{Path=".pytest_cache"; Desc="Pytest cache"; Size=$size}
}

# 4. MyPy cache
if (Test-Path ".mypy_cache") {
    $size = (Get-ChildItem .mypy_cache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $itemsToRemove += @{Path=".mypy_cache"; Desc="MyPy cache"; Size=$size}
}

# 5. Temp files
Get-ChildItem -Path . -Recurse -File -Filter ".tmp_*" -ErrorAction SilentlyContinue | ForEach-Object {
    $itemsToRemove += @{Path=$_.FullName; Desc="Temp file"; Size=$_.Length}
}

# 6. Old backup
if (Test-Path "backup_runtime.py") {
    $size = (Get-Item backup_runtime.py).Length
    $itemsToRemove += @{Path="backup_runtime.py"; Desc="Old backup"; Size=$size}
}

# 7. Duplicate data
if (Test-Path "web/src/data/scenarios") {
    $size = (Get-ChildItem web/src/data/scenarios -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $itemsToRemove += @{Path="web/src/data/scenarios"; Desc="Duplicate data"; Size=$size}
}

# Display items
Write-Host "Items to cleanup:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$totalSize = 0
$index = 1
foreach ($item in $itemsToRemove) {
    $sizeMB = [math]::Round($item.Size / 1MB, 2)
    $totalSize += $item.Size
    Write-Host "[$index] $($item.Desc)" -ForegroundColor White
    Write-Host "    Path: $($item.Path)" -ForegroundColor Gray
    Write-Host "    Size: $sizeMB MB" -ForegroundColor Gray
    Write-Host ""
    $index++
}

$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "Total to free: $totalSizeMB MB" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] No files deleted" -ForegroundColor Cyan
    exit 0
}

# Confirm
if (-not $Force) {
    $confirm = Read-Host "Delete these files? (y/N)"
    if ($confirm -ne 'y') {
        Write-Host "Cancelled" -ForegroundColor Yellow
        exit 0
    }
}

# Delete
Write-Host "Cleaning..." -ForegroundColor Yellow
$success = 0
$failed = 0

foreach ($item in $itemsToRemove) {
    try {
        if (Test-Path $item.Path) {
            Remove-Item -Path $item.Path -Recurse -Force -ErrorAction Stop
            Write-Host "[OK] Deleted: $($item.Desc)" -ForegroundColor Green
            $success++
        }
    }
    catch {
        Write-Host "[FAIL] $($item.Path): $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done!" -ForegroundColor Green
Write-Host "Success: $success, Failed: $failed" -ForegroundColor White
Write-Host "Freed: $totalSizeMB MB" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. cd web && npm install" -ForegroundColor White
Write-Host "2. cd web && npm run dev" -ForegroundColor White
Write-Host "3. git add -A && git commit" -ForegroundColor White
