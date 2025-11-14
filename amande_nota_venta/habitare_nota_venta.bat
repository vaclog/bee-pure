FOR /F "tokens=*" %%A IN ('DATE/T') DO FOR %%B IN (%%A) DO SET Today=%%B

FOR /F "tokens=1-3 delims=/-" %%A IN ("%Today%") DO (
    SET DayMonth=%%A
    SET MonthDay=%%B
    SET Year=%%C
)

SET FILENAMELOG=%Year%-%MonthDay%-%DayMonth%
REM set RUN=C:\Users\ValkUser\Downloads\pdi-ce-8.0.0.0-28\data-integration
set FILE_RUN=C:\Users\ValkUser\Documents\NOTA_VENTA\bee-pure\habitare_nota_venta\

REM Activar ambiente virtual
call "%FILE_RUN%\.venv\Scripts\activate.bat"

REM Instalar requirements
pip install -r "%FILE_RUN%\requirements.txt"

python "%FILE_RUN%\main.py"  >> C:\LOGS\habitare_nova_venta_%FILENAMELOG%.txt 2>&1