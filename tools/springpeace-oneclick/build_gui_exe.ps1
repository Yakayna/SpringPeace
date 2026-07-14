# SPDX-License-Identifier: GPL-3.0-or-later
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = if ($env:SPRINGPEACE_PYTHON) { $env:SPRINGPEACE_PYTHON } else { 'python' }
& $PythonExe -m pip install --user -r (Join-Path $ScriptDir 'requirements.txt')

$DataArgs = @(
  '--add-data', "$(Join-Path $ScriptDir 'presets.json');.",
  '--add-data', "$(Join-Path $ScriptDir 'patches\xspy-generate-target-compat.patch');patches",
  '--add-data', "$(Join-Path $ScriptDir 'assets\mika.png');assets",
  '--add-data', "$(Join-Path $ScriptDir 'assets\mika.ico');assets"
)
$VendorDir = Join-Path $ScriptDir 'vendor'
if (Test-Path $VendorDir) {
  $DataArgs += @('--add-data', "$VendorDir;vendor")
}

& $PythonExe -m PyInstaller `
  --onefile `
  --windowed `
  --name SpringPeace `
  --icon (Join-Path $ScriptDir 'assets\mika.ico') `
  --collect-submodules lz4 `
  @DataArgs `
  --distpath (Join-Path $ScriptDir 'dist') `
  --workpath (Join-Path $ScriptDir 'build-gui') `
  --specpath (Join-Path $ScriptDir 'build-gui') `
  (Join-Path $ScriptDir 'springpeace_gui.py')
Write-Host "Built: $(Join-Path $ScriptDir 'dist\SpringPeace.exe')"
