@echo off
setlocal

:: Ruta absoluta a esta carpeta (donde vive el .bat)
set "ETL_DIR=%~dp0"
set "PYTHON=%ETL_DIR%.venv\Scripts\python.exe"

:: Verificar que el venv existe
if not exist "%PYTHON%" (
    echo [ERROR] No se encontro el entorno virtual en %ETL_DIR%.venv
    echo Ejecutar primero: python -m venv .venv  ^&^&  python -m pip install -r requirements.txt
    exit /b 1
)

:: Ejecutar desde la carpeta del ETL para que los imports relativos funcionen
cd /d "%ETL_DIR%"

echo [%date% %time%] Iniciando ETL OV...
"%PYTHON%" -m src.main
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% neq 0 (
    echo [%date% %time%] ETL OV finalizo con error (codigo %EXIT_CODE%).
) else (
    echo [%date% %time%] ETL OV finalizo correctamente.
)

exit /b %EXIT_CODE%
