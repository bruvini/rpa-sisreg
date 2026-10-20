# Compilar somente em Windows autorizado ou GitHub Actions com dados sintéticos.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python scripts/preparar_compilacao.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SISREG_Login --paths src --version-file versao_windows.txt --collect-all playwright --collect-all pymupdf --collect-all openpyxl src/sisreg_login.py
if (-not (Test-Path dist/SISREG_Login.exe)) { throw 'EXE nao gerado.' }
$sha = (Get-FileHash dist/SISREG_Login.exe -Algorithm SHA256).Hash
"SISREG_Login.exe SHA256: $sha" | Out-File -FilePath dist/SHA256.txt -Encoding utf8
Write-Host "Executavel v0.6.0: dist/SISREG_Login.exe"
