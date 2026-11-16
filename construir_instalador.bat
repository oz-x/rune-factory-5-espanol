@echo off
rem Genera dist\RF5-Espanol-Instalador.exe (requiere: pip install pyinstaller UnityPy)
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name RF5-Espanol-Instalador ^
  --paths "%~dp0tools" --add-data "%~dp0mod\texto;mod\texto" --add-data "%~dp0tools\adv_commands.json;." ^
  --collect-all UnityPy --collect-data archspec ^
  --distpath dist --workpath build --specpath build instalador.py
