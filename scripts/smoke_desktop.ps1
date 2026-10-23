# SPDX-License-Identifier: AGPL-3.0-only
param(
    [string]$DistDir = 'work/desktop-dist',
    [string]$ReportDir = 'work/desktop-smoke',
    [string]$Version = '1.2.0',
    [Parameter(Mandatory=$true)][string]$SourceCommit
)
$ErrorActionPreference = 'Stop'
$distRoot = (Resolve-Path -LiteralPath $DistDir).Path
$reportRoot = [IO.Path]::GetFullPath($ReportDir)
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$portableZip = Join-Path $distRoot "UI_Center_v${Version}_Windows_x64_Portable.zip"
$singleExe = Join-Path $distRoot "UI_Center_v${Version}_Windows_x64.exe"
$inputHashes = @{}
foreach ($inputFile in @($portableZip,$singleExe)) {
    $inputHashes[$inputFile] = (Get-FileHash -LiteralPath $inputFile -Algorithm SHA256).Hash.ToLowerInvariant()
}
$isolatedRoot = Join-Path $reportRoot '中文 路径'
$unrelatedCwd = Join-Path $reportRoot 'empty-cwd'
if (Test-Path -LiteralPath $isolatedRoot) { throw "Fresh smoke directory required: $isolatedRoot" }
New-Item -ItemType Directory -Path $isolatedRoot,$unrelatedCwd | Out-Null
Expand-Archive -LiteralPath $portableZip -DestinationPath $isolatedRoot
$portableCandidates = @(Get-ChildItem -LiteralPath $isolatedRoot -File -Recurse -Filter 'UI_Center.exe')
if ($portableCandidates.Count -ne 1) { throw 'Portable archive must contain one UI_Center.exe' }
$singleCopy = Join-Path $isolatedRoot 'UI_Center_单文件.exe'
Copy-Item -LiteralPath $singleExe -Destination $singleCopy
$summary = @()
$oldPythonPath = $env:PYTHONPATH
$oldPythonHome = $env:PYTHONHOME
$oldTclLibrary = $env:TCL_LIBRARY
$oldTkLibrary = $env:TK_LIBRARY
try {
    $env:PYTHONPATH = $null
    $env:PYTHONHOME = $null
    $env:TCL_LIBRARY = $null
    $env:TK_LIBRARY = $null
    foreach ($package in @(
        @{ Name='portable'; Exe=$portableCandidates[0].FullName; Artifact=$portableZip },
        @{ Name='single'; Exe=$singleCopy; Artifact=$singleExe }
    )) {
        $reportFile = Join-Path $reportRoot ("smoke-" + $package.Name + ".json")
        $executableHash = (Get-FileHash -LiteralPath $package.Exe -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($package.Name -eq 'single' -and $executableHash -ne $inputHashes[$singleExe]) { throw 'Single EXE copy differs from input' }
        $timer = [Diagnostics.Stopwatch]::StartNew()
        $processInfo = [Diagnostics.ProcessStartInfo]::new()
        $processInfo.FileName = $package.Exe
        $processInfo.Arguments = '--smoke-test "' + $reportFile + '"'
        $processInfo.WorkingDirectory = $unrelatedCwd
        $processInfo.UseShellExecute = $false
        $processInfo.CreateNoWindow = $true
        $processInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
        $process = [Diagnostics.Process]::Start($processInfo)
        if (-not $process.WaitForExit(60000)) {
            [void]$process.CloseMainWindow()
            throw ("Frozen smoke did not exit in 60 seconds: " + $package.Name)
        }
        $timer.Stop()
        if ($process.ExitCode -ne 0) { throw ("Frozen smoke failed: " + $package.Name + ", exit " + $process.ExitCode) }
        $report = Get-Content -LiteralPath $reportFile -Raw | ConvertFrom-Json
        if ($report.status -ne 'passed' -or $report.version -ne $Version -or $report.commit -ne $SourceCommit -or $report.frozen -ne $true) {
            throw ("Frozen smoke identity/status mismatch: " + $package.Name)
        }
        if (@($report.checks | Where-Object { $_.passed -ne $true }).Count -gt 0) { throw 'Frozen smoke contains failed checks' }
        $artifactHash = (Get-FileHash -LiteralPath $package.Artifact -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($artifactHash -ne $inputHashes[$package.Artifact] -or $executableHash -ne (Get-FileHash -LiteralPath $package.Exe -Algorithm SHA256).Hash.ToLowerInvariant()) {
            throw 'The smoke input or executable changed during validation'
        }
        $artifact = [ordered]@{name=[IO.Path]::GetFileName($package.Artifact);bytes=(Get-Item -LiteralPath $package.Artifact).Length;sha256=$artifactHash}
        $report | Add-Member -NotePropertyName artifact -NotePropertyValue $artifact
        $report | Add-Member -NotePropertyName executable_sha256 -NotePropertyValue $executableHash
        $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportFile -Encoding utf8
        $summary += [ordered]@{
            package=$package.Name
            status=$report.status
            version=$report.version
            commit=$report.commit
            checks=@($report.checks).Count
            smoke_elapsed_ms=$timer.ElapsedMilliseconds
            artifact=$artifact
        }
    }
} finally {
    $env:PYTHONPATH=$oldPythonPath
    $env:PYTHONHOME=$oldPythonHome
    $env:TCL_LIBRARY=$oldTclLibrary
    $env:TK_LIBRARY=$oldTkLibrary
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reportRoot 'smoke-summary.json') -Encoding utf8
$summary | ConvertTo-Json -Depth 5
