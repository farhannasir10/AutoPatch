# kick the API from repo root
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
}
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
