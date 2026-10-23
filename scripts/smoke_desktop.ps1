# SPDX-License-Identifier: AGPL-3.0-only
param(
    [string]$DistDir = 'work/v1.2.3/desktop-dist',
    [string]$ReportDir = 'work/v1.2.3/desktop-smoke',
    [string]$Version = '1.2.3',
    [Parameter(Mandatory=$true)][string]$SourceCommit
)
$ErrorActionPreference = 'Stop'

function Move-IsolatedSmokeRoot {
    param([string]$SourceRoot, [string]$TargetRoot)
    $sourceFull = [IO.Path]::GetFullPath($SourceRoot)
    $targetFull = [IO.Path]::GetFullPath($TargetRoot)
    $reportFull = [IO.Path]::GetFullPath($reportRoot).TrimEnd('\', '/')
    $reportPrefix = $reportFull + [IO.Path]::DirectorySeparatorChar
    foreach ($candidate in @($sourceFull, $targetFull)) {
        if ($candidate.TrimEnd('\', '/') -eq $reportFull -or -not $candidate.StartsWith($reportPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Smoke relocation must stay strictly inside the report directory: $candidate"
        }
    }
    if ([IO.Path]::GetPathRoot($sourceFull) -ne [IO.Path]::GetPathRoot($targetFull)) {
        throw 'Smoke relocation must stay on the same volume'
    }
    if (-not (Test-Path -LiteralPath $sourceFull -PathType Container)) {
        throw "Smoke relocation source directory is missing: $sourceFull"
    }
    if (Test-Path -LiteralPath $targetFull) {
        throw "Smoke relocation target already exists: $targetFull"
    }
    # Check existing ancestors as well as the entire extracted tree before
    # issuing a literal, same-shell move. Never traverse or move a junction.
    foreach ($path in @($sourceFull, [IO.Path]::GetDirectoryName($targetFull))) {
        $directory = Get-Item -LiteralPath $path -Force
        while ($null -ne $directory) {
            if (($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Smoke relocation cannot use a reparse point: $($directory.FullName)"
            }
            $directory = $directory.Parent
        }
    }
    $reparse = @(Get-ChildItem -LiteralPath $sourceFull -Recurse -Force |
        Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 })
    if ($reparse.Count -gt 0) { throw "Smoke relocation contains a reparse point: $($reparse[0].FullName)" }
    Move-Item -LiteralPath $sourceFull -Destination $targetFull
    if ((Test-Path -LiteralPath $sourceFull) -or -not (Test-Path -LiteralPath $targetFull -PathType Container)) {
        throw 'Smoke relocation did not preserve the expected directory boundary'
    }
}

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
$relocatedRoot = Join-Path $reportRoot '迁移 后中文路径'
$unrelatedCwd = Join-Path $reportRoot 'empty-cwd'
if (Test-Path -LiteralPath $isolatedRoot) { throw "Fresh smoke directory required: $isolatedRoot" }
New-Item -ItemType Directory -Path $isolatedRoot,$unrelatedCwd | Out-Null
Expand-Archive -LiteralPath $portableZip -DestinationPath $isolatedRoot
$portableCandidates = @(Get-ChildItem -LiteralPath $isolatedRoot -File -Recurse -Filter 'UI_Center.exe')
if ($portableCandidates.Count -ne 1) { throw 'Portable archive must contain one UI_Center.exe' }
$portableRelative = [IO.Path]::GetRelativePath($isolatedRoot, $portableCandidates[0].FullName)
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
    foreach ($phase in @('original', 'relocated')) {
        $phaseRoot = $isolatedRoot
        $reportPrefix = ''
        if ($phase -eq 'relocated') {
            # Both original processes have exited before moving their complete
            # directory, including the default profile written by the probe.
            Move-IsolatedSmokeRoot -SourceRoot $isolatedRoot -TargetRoot $relocatedRoot
            $phaseRoot = $relocatedRoot
            $reportPrefix = 'relocated-'
        }
        foreach ($package in @(
            @{ Name='portable'; Exe=(Join-Path $phaseRoot $portableRelative); Artifact=$portableZip },
            @{ Name='single'; Exe=(Join-Path $phaseRoot 'UI_Center_单文件.exe'); Artifact=$singleExe }
        )) {
            $reportFile = Join-Path $reportRoot ("smoke-" + $reportPrefix + $package.Name + ".json")
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
            # Only this child may exercise default profile writes in the explicitly
            # bounded disposable extraction; ordinary --smoke-test calls do not.
            $processInfo.Environment['UI_CENTER_SMOKE_SANDBOX'] = $reportRoot
            $process = [Diagnostics.Process]::Start($processInfo)
            if (-not $process.WaitForExit(60000)) {
                [void]$process.CloseMainWindow()
                throw ("Frozen smoke did not exit in 60 seconds: " + $package.Name)
            }
            $timer.Stop()
            if ($process.ExitCode -ne 0) {
                if (Test-Path -LiteralPath $reportFile) {
                    Write-Host (Get-Content -LiteralPath $reportFile -Raw)
                }
                throw ("Frozen smoke failed: " + $package.Name + ", exit " + $process.ExitCode)
            }
            $report = Get-Content -LiteralPath $reportFile -Raw | ConvertFrom-Json
            if ($report.status -ne 'passed' -or $report.version -ne $Version -or $report.commit -ne $SourceCommit -or $report.frozen -ne $true) {
                throw ("Frozen smoke identity/status mismatch: " + $package.Name)
            }
            if (@($report.checks | Where-Object { $_.passed -ne $true }).Count -gt 0) { throw 'Frozen smoke contains failed checks' }
            $expectedProgram = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($package.Exe))
            $expectedProfile = Join-Path (Join-Path $expectedProgram 'data') 'preferences.json'
            if ([IO.Path]::GetFullPath([string]$report.locations.program_directory) -ne $expectedProgram -or [IO.Path]::GetFullPath([string]$report.locations.default_preferences_file) -ne $expectedProfile) {
                throw ("Frozen default profile is not beside the actual executable: " + $phase + '/' + $package.Name)
            }
            if ($report.default_profile_after.theme -ne 'sage' -or $report.default_profile_after.font_scale -ne 125 -or $report.default_profile_after.motion -ne 'reduced') {
                throw ("Default profile probe did not persist/reload its values: " + $phase + '/' + $package.Name)
            }
            if ($phase -eq 'relocated' -and ($report.default_profile_before.theme -ne 'sage' -or $report.default_profile_before.font_scale -ne 125 -or $report.default_profile_before.motion -ne 'reduced')) {
                throw ("Relocated default profile did not retain the original settings: " + $package.Name)
            }
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
                phase=$phase
                status=$report.status
                version=$report.version
                commit=$report.commit
                checks=@($report.checks).Count
                smoke_elapsed_ms=$timer.ElapsedMilliseconds
                artifact=$artifact
            }
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
