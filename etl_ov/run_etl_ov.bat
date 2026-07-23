@echo off
setlocal

:: Ruta absoluta a esta carpeta (donde vive el .bat)
set "ETL_DIR=%~dp0"
set "PYTHON=%ETL_DIR%.venv\Scripts\python.exe"

:: Log diario en %TEMP%\etl_ov_YYYYMMDD.log
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "FECHA=%%d"
set "LOGFILE=%TEMP%\etl_ov_%FECHA%.log"

:: Verificar que el venv existe
if not exist "%PYTHON%" (
    echo [%date% %time%] [ERROR] No se encontro el entorno virtual en %ETL_DIR%.venv >> "%LOGFILE%"
    echo [ERROR] No se encontro el entorno virtual en %ETL_DIR%.venv
    echo Ejecutar primero: python -m venv .venv  ^&^&  python -m pip install -r requirements.txt
    exit /b 1
)

:: Ejecutar desde la carpeta del ETL para que los imports relativos funcionen
cd /d "%ETL_DIR%"

echo [%date% %time%] Iniciando ETL OV... >> "%LOGFILE%"
"%PYTHON%" -m src.main >> "%LOGFILE%" 2>&1
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% neq 0 (
    echo [%date% %time%] ETL OV finalizo con error (codigo %EXIT_CODE%). >> "%LOGFILE%"
) else (
    echo [%date% %time%] ETL OV finalizo correctamente. >> "%LOGFILE%"
)

echo Log guardado en: %LOGFILE%
exit /b %EXIT_CODE%
