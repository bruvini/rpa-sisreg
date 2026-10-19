# Execute SOMENTE em computador Windows autorizado pela TI, com Python já
# disponível no AMBIENTE DE COMPILAÇÃO. A estação da Joice não precisa Python.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SISREG_Login --collect-all playwright src/sisreg_login.py
Get-FileHash dist\SISREG_Login.exe -Algorithm SHA256 | Format-List
Write-Host 'Pronto: dist\SISREG_Login.exe'
