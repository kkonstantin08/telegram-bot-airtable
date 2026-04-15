$ErrorActionPreference = "Stop"

$Python = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}

& $Python -m compileall artbot scripts tests
& $Python -m pytest -q
& $Python scripts/local_e2e.py
