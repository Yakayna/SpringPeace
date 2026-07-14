# SPDX-License-Identifier: GPL-3.0-or-later
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = if ($env:SPRINGPEACE_PYTHON) { $env:SPRINGPEACE_PYTHON } else { 'python' }
& $PythonExe -m pip install --user -r (Join-Path $ScriptDir 'requirements.txt')
& $PythonExe -m PyInstaller `
  --onefile `
  --name springpeace-oneclick `
  --collect-submodules lz4 `
  --add-data "$(Join-Path $ScriptDir 'presets.json');." `
  --add-data "$(Join-Path $ScriptDir 'patches\xspy-generate-target-compat.patch');patches" `
  --distpath (Join-Path $ScriptDir 'dist') `
  --workpath (Join-Path $ScriptDir 'build') `
  --specpath (Join-Path $ScriptDir 'build') `
  (Join-Path $ScriptDir 'springpeace.py')
Write-Host "Built: $(Join-Path $ScriptDir 'dist\springpeace-oneclick.exe')"
