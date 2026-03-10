param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$DialogTitle = "hitl-self-test",
    [ValidateSet("none", "reject", "accept", "edit_accept")]
    [string]$Decision = "none",
    [string]$EditedContent = "# Edited by hitl_self_test`n",
    [switch]$RunUnitTests
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "[STEP] $msg" -ForegroundColor Cyan
}

function Write-Pass([string]$msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
}

function Write-WarnMsg([string]$msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Write-Fail([string]$msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
}

function Invoke-Json {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [object]$Body = $null
    )

    try {
        if ($null -ne $Body) {
            $json = $Body | ConvertTo-Json -Depth 20
            return Invoke-RestMethod -Uri $Uri -Method $Method -ContentType "application/json" -Body $json
        }
        return Invoke-RestMethod -Uri $Uri -Method $Method
    }
    catch {
        throw "Request failed: $Method $Uri`n$($_.Exception.Message)"
    }
}

function Invoke-JsonSafe {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [object]$Body = $null
    )

    try {
        $result = Invoke-Json -Method $Method -Uri $Uri -Body $Body
        return @{ ok = $true; data = $result }
    }
    catch {
        return @{ ok = $false; error = $_.Exception.Message }
    }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"

Write-Step "Using repo root: $repoRoot"
if (Test-Path $venvPython) {
    Write-Pass "Virtual env python found: $venvPython"
}
else {
    Write-WarnMsg "Virtual env python not found at $venvPython"
}

Write-Step "Backend health check: GET $BaseUrl/"
$rootResp = Invoke-Json -Method "GET" -Uri "$BaseUrl/"
if ($rootResp.version) {
    Write-Pass "Backend reachable, version=$($rootResp.version)"
}
else {
    Write-WarnMsg "Backend reachable but version field missing"
}

$hasHitlRoute = $false
$openApiCall = Invoke-JsonSafe -Method "GET" -Uri "$BaseUrl/openapi.json"
if ($openApiCall.ok) {
    $paths = $openApiCall.data.paths.PSObject.Properties.Name
    $hasHitlRoute = $paths -contains "/api/skill-edits/pending"
    if ($hasHitlRoute) {
        Write-Pass "HITL route detected in OpenAPI: /api/skill-edits/pending"
    }
    else {
        Write-WarnMsg "Current backend OpenAPI does not expose /api/skill-edits/pending"
    }
}
else {
    Write-WarnMsg "Cannot read OpenAPI for route check: $($openApiCall.error)"
}

Write-Step "Create dialog via POST $BaseUrl/api/dialogs"
$createResp = Invoke-Json -Method "POST" -Uri "$BaseUrl/api/dialogs" -Body @{ title = $DialogTitle }
if (-not $createResp.success) {
    throw "Create dialog response indicates failure"
}
$dialogId = $createResp.data.id
Write-Pass "Dialog created: $dialogId"

Write-Step "List pending skill edits for dialog"
$pendingCall = Invoke-JsonSafe -Method "GET" -Uri "$BaseUrl/api/skill-edits/pending?dialog_id=$dialogId"
if (-not $pendingCall.ok) {
    Write-WarnMsg "Skill-edit endpoint unavailable on current backend: $($pendingCall.error)"
    Write-WarnMsg "If you expect HITL APIs, ensure backend is running the main_new app with skill-edit routes."
    $pendingList = @()
}
else {
    $pendingResp = $pendingCall.data
    if (-not $pendingResp.success) {
        throw "Pending list response indicates failure"
    }
    $pendingList = @($pendingResp.data)
    Write-Host "Pending count: $($pendingList.Count)"
}

if ($pendingList.Count -eq 0) {
    Write-WarnMsg "No pending approvals yet. Trigger a skill edit in UI first, then rerun this script."
}
else {
    $first = $pendingList[0]
    Write-Pass "First pending approval_id=$($first.approval_id), path=$($first.path)"

    if ($Decision -ne "none") {
        Write-Step "Apply decision '$Decision' to approval_id=$($first.approval_id)"
        $decisionBody = @{ decision = $Decision }
        if ($Decision -eq "edit_accept") {
            $decisionBody.edited_content = $EditedContent
        }

        $decisionCall = Invoke-JsonSafe -Method "POST" -Uri "$BaseUrl/api/skill-edits/$($first.approval_id)/decision" -Body $decisionBody
        if (-not $decisionCall.ok) {
            Write-Fail "Decision API unavailable: $($decisionCall.error)"
        }
        elseif ($decisionCall.data.success) {
            $decisionResp = $decisionCall.data
            Write-Pass "Decision applied. New status=$($decisionResp.data.status)"
        }
        else {
            Write-Fail "Decision call returned success=false: $($decisionCall.data.message)"
        }
    }
    else {
        Write-WarnMsg "Decision not applied (Decision=none)."
    }
}

if ($RunUnitTests) {
    if (-not (Test-Path $venvPython)) {
        Write-Fail "Skipping unittest: venv python not found"
    }
    else {
        Write-Step "Run regression tests with venv"
        Push-Location $repoRoot
        try {
            & $venvPython -m unittest test_skill_edit_hitl.py test_skill_edit_hitl_api.py
            if ($LASTEXITCODE -eq 0) {
                Write-Pass "Unit tests passed"
            }
            else {
                Write-Fail "Unit tests failed with exit code $LASTEXITCODE"
            }
        }
        finally {
            Pop-Location
        }
    }
}

Write-Host "`nDone."
