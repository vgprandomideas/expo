$packagesPath = Join-Path $PSScriptRoot ".packages"
$pythonPath = "C:\Users\Verslan CEO\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path $packagesPath)) {
    Write-Error "Missing .packages directory. Install dependencies first with: python -m pip install -r requirements.txt --target .packages"
    exit 1
}

& $pythonPath (Join-Path $PSScriptRoot "bootstrap_streamlit.py") @args
