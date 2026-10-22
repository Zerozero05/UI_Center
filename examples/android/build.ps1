param(
    [Parameter(Mandatory=$true)][string]$ToolingRoot,
    [string[]]$Tasks = @('assembleDebug','lintDebug','assembleDebugAndroidTest')
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$workRoot = Join-Path $repoRoot 'work/android'
$jdk = Get-ChildItem -LiteralPath (Join-Path $ToolingRoot 'jdk') -Directory | Select-Object -First 1
$gradle = Join-Path $ToolingRoot 'gradle/gradle-8.9/bin/gradle.bat'
$readOnlyDeps = Join-Path $ToolingRoot 'gradle-home/caches'
if (!$jdk -or !(Test-Path -LiteralPath $gradle) -or !(Test-Path -LiteralPath (Join-Path $readOnlyDeps 'modules-2'))) {
    throw 'ToolingRoot must contain an installed JDK17, Gradle8.9 and a populated gradle-home dependency cache.'
}
$names = @('JAVA_HOME','ANDROID_HOME','ANDROID_SDK_ROOT','ANDROID_USER_HOME','GRADLE_USER_HOME','GRADLE_RO_DEP_CACHE','PATH')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
    $env:JAVA_HOME = $jdk.FullName
    $env:ANDROID_HOME = Join-Path $ToolingRoot 'sdk'
    $env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
    $env:ANDROID_USER_HOME = Join-Path $workRoot 'android-home'
    $env:GRADLE_USER_HOME = Join-Path $workRoot 'gradle-home'
    $env:GRADLE_RO_DEP_CACHE = $readOnlyDeps
    $env:PATH = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:PATH
    & $gradle '-p' $PSScriptRoot '--project-cache-dir' (Join-Path $workRoot 'project-cache') '--offline' '--no-daemon' '--console=plain' @Tasks
    if ($LASTEXITCODE -ne 0) { throw 'Android offline build/check failed. No dependencies were downloaded.' }
    $testClasses = Join-Path $workRoot 'state-tests'
    New-Item -ItemType Directory -Path $testClasses -Force | Out-Null
    & (Join-Path $env:JAVA_HOME 'bin/javac.exe') '-encoding' 'UTF-8' '-d' $testClasses `
        (Join-Path $repoRoot 'components/android/src/main/java/cn/local/uicenter/TaskState.java') `
        (Join-Path $repoRoot 'tests/android/TaskStateTest.java')
    if ($LASTEXITCODE -ne 0) { throw 'TaskState test compilation failed' }
    & (Join-Path $env:JAVA_HOME 'bin/java.exe') '-cp' $testClasses 'TaskStateTest'
    if ($LASTEXITCODE -ne 0) { throw 'TaskState regression failed' }
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
