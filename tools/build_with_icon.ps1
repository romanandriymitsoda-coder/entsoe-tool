Param(
  [string]$ImagePath = "assets/ey_logo.png"
)

$ErrorActionPreference = 'Stop'

# Ensure venv exists
if (-not (Test-Path ".venv/Scripts/python.exe")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}

# Install Pillow for PNG/JPG -> ICO conversion
& .\.venv\Scripts\python -m pip install -q --upgrade pip > $null
& .\.venv\Scripts\python -m pip install -q pillow > $null

# Normalize paths
$icoPath = "assets/ey_logo.ico"
$imgExt = [IO.Path]::GetExtension($ImagePath).ToLowerInvariant()

if ($imgExt -eq ".ico") {
  Copy-Item -Force $ImagePath $icoPath
} else {
  # Write converter script
  $py = @'
from PIL import Image
import os, sys
src = sys.argv[1]
dst = sys.argv[2]
img = Image.open(src).convert('RGBA')
size = max(img.size)
canvas = Image.new('RGBA', (size, size), (255, 255, 255, 0))
canvas.paste(img, ((size - img.width)//2, (size - img.height)//2), img)
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
canvas.save(dst, sizes=sizes)
'@
  $tmp = "tools/make_icon.py"
  $py | Set-Content -NoNewline $tmp
  & .\.venv\Scripts\python $tmp $ImagePath $icoPath
}

if (-not (Test-Path $icoPath)) { throw "ICO not created: $icoPath" }

# Build final EXE (no code changes). We keep the working noverify runtime hook.
if (-not (Test-Path "hooks/pyi_rth_requests_noverify.py")) {
  @"import urllib3, requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_old = requests.sessions.Session.request
def _patched(self, method, url, **kwargs):
    kwargs.setdefault('verify', False)
    return _old(self, method, url, **kwargs)
requests.sessions.Session.request = _patched
"@ | Set-Content -NoNewline hooks/pyi_rth_requests_noverify.py
}

# Remove old binary if present (avoid permission issues)
if (Test-Path "dist/EntsoeTool.exe") { Remove-Item -Force "dist/EntsoeTool.exe" }

& .\.venv\Scripts\pyinstaller --noconfirm --onefile --noconsole --name EntsoeTool --icon $icoPath --runtime-hook hooks\pyi_rth_requests_noverify.py main.py

Write-Host "Built: dist/EntsoeTool.exe"
