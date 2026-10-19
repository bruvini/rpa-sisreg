# Executar em Windows de desenvolvimento autorizado ou no GitHub Actions.
# A estacao da SMS nao necessita Python instalado.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SISREG_Login --paths src --collect-all playwright --collect-all pymupdf --collect-all openpyxl src/sisreg_login.py
Get-FileHash dist\SISREG_Login.exe -Algorithm SHA256 | Format-List
Write-Host 'Pronto: dist\SISREG_Login.exe'
