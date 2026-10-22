param([Parameter(Mandatory=$true)][string]$ToolingRoot)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$consumer = Join-Path $repoRoot ('work/android/source-consumer-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $consumer | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'consumer/app') -Destination $consumer -Recurse
foreach ($name in @('settings.gradle','build.gradle','gradle.properties')) {
    Copy-Item -LiteralPath (Join-Path $repoRoot ('examples/android/' + $name)) -Destination $consumer
}
$componentTarget = Join-Path $consumer 'app/src/main/java/cn/local/uicenter'
New-Item -ItemType Directory -Path $componentTarget -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $repoRoot 'components/android/src/main/java/cn/local/uicenter') -Filter '*.java' |
    Copy-Item -Destination $componentTarget
$assets = Join-Path $consumer 'app/src/main/assets'
New-Item -ItemType Directory -Path $assets -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repoRoot 'tokens/design-tokens.json') -Destination $assets
Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination $consumer
$names = @('JAVA_HOME','ANDROID_HOME','ANDROID_SDK_ROOT','ANDROID_USER_HOME','GRADLE_USER_HOME','GRADLE_RO_DEP_CACHE','PATH')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
    $jdk = Get-ChildItem -LiteralPath (Join-Path $ToolingRoot 'jdk') -Directory | Select-Object -First 1
    $env:JAVA_HOME = $jdk.FullName
    $env:ANDROID_HOME = Join-Path $ToolingRoot 'sdk'; $env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
    $env:ANDROID_USER_HOME = Join-Path $repoRoot 'work/android/android-home'
    $env:GRADLE_USER_HOME = Join-Path $repoRoot 'work/android/gradle-home'
    $env:GRADLE_RO_DEP_CACHE = Join-Path $ToolingRoot 'gradle-home/caches'
    $env:PATH = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:PATH
    & (Join-Path $ToolingRoot 'gradle/gradle-8.9/bin/gradle.bat') '-p' $consumer '--offline' '--no-daemon' '--console=plain' 'assembleDebug' 'lintDebug'
    if ($LASTEXITCODE -ne 0) { throw 'Independent Android consumer build/lint failed' }
    $copiedTokens = Join-Path $assets 'design-tokens.json'
    if ((Get-FileHash -LiteralPath $copiedTokens).Hash -ne (Get-FileHash -LiteralPath (Join-Path $repoRoot 'tokens/design-tokens.json')).Hash) {
        throw 'Copied tokens differ from the selected source'
    }
    Write-Output ('Independent Android consumer passed: ' + $consumer)
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
