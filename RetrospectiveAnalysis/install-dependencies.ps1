Write-Output "Installing. It may take a few minutes. The window will be automatically closed when it's done."
python -m venv .\.venv
.\.venv\Scripts\Activate.ps1
pip install -r .\requirements.txt