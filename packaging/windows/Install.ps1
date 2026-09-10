[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Programs\VEMO'),
    [switch]$Apply,
    [switch]$NoShortcut
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-PlainPath([string]$Path) {
    $item = [IO.Path]::GetFullPath($Path)
    while ($item) {
        if (Test-Path -LiteralPath $item) {
            if ((Get-Item -LiteralPath $item -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Linked paths are not supported: $item"
            }
        }
        $item = [IO.Path]::GetDirectoryName($item)
    }
}

function Assert-Package([string]$Root, $Manifest) {
    foreach ($entry in $Manifest.files.PSObject.Properties) {
        $name = $entry.Name
        if ($name -match '(^/|\\|:|(^|/)\.\.?(/|$))') { throw "Unsafe package path: $name" }
        $file = Join-Path $Root $name
        Assert-PlainPath $file
        if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing package file: $name" }
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
            throw "Package integrity failure: $name"
        }
    }
}

Assert-PlainPath $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package.json') -Raw | ConvertFrom-Json
if ($manifest.schema_version -ne 1 -or $manifest.build_id -notmatch '^[a-f0-9]{16}$') {
    throw 'Unsupported package manifest'
}
Assert-Package $PSScriptRoot $manifest
$root = [IO.Path]::GetFullPath($InstallRoot)
$target = Join-Path $root $manifest.build_id
Assert-PlainPath $target
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) ("VEMO Supervision " + $manifest.build_id + '.lnk')
Write-Output "Verified Windows x64 package: $($manifest.build_id)"
Write-Output "Install location: $target"
Write-Output 'No administrator access, global PATH changes, background service or automatic project enrollment.'
if (!$Apply) { Write-Output 'Preview only. Run again with -Apply to install.'; return }
if (Test-Path -LiteralPath $target) {
    Assert-Package $target $manifest
    if ((Get-FileHash -LiteralPath (Join-Path $target 'package.json')).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'package.json')).Hash) { throw 'Existing manifest differs' }
} else {
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    $staging = Join-Path $root ('.install-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    # Keep a failed staging directory for inspection; never delete an unknown directory tree.
    foreach ($entry in $manifest.files.PSObject.Properties) {
        $destination = Join-Path $staging $entry.Name
        New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $entry.Name) -Destination $destination
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'package.json') -Destination (Join-Path $staging 'package.json')
    Assert-Package $staging $manifest
    & (Join-Path $staging 'runtime\python.exe') -I -S (Join-Path $staging 'framework\bin\vemo') --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Bundled runtime failed: $LASTEXITCODE" }
    # Both checked absolute paths are direct children of the selected installation root.
    if ([IO.Path]::GetDirectoryName($staging) -ne $root -or [IO.Path]::GetDirectoryName($target) -ne $root) {
        throw 'Installation path containment failure'
    }
    Move-Item -LiteralPath $staging -Destination $target
}
if (!$NoShortcut) {
    Assert-PlainPath $shortcut
    if (!(Test-Path -LiteralPath $shortcut)) {
        $link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
        $link.TargetPath = Join-Path $target 'vemo.cmd'
        $link.WorkingDirectory = $target
        $link.Description = 'VEMO project supervision setup and maintenance'
        $link.Save()
    }
    Write-Output "Start menu shortcut: $shortcut"
}
Write-Output "Installed: $target\vemo.cmd"
