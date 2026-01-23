import csv
from openpyxl import Workbook


def detect_encoding(file_path: str) -> str:
    """
    Detecta el encoding de un archivo probando diferentes codificaciones.
    """
    with open(file_path, 'rb') as f:
        raw = f.read()

    # Verificar si es UTF-8 válido
    try:
        raw.decode('utf-8')
        # Si tiene BOM, usar utf-8-sig
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # Si no es UTF-8 válido, usar cp1252 (Windows)
    return 'cp1252'


def csv_to_xlsx(csv_path: str, xlsx_path: str, delimiter: str = ',', encoding: str = None) -> None:
    """
    Convierte un archivo CSV a formato XLSX.

    Args:
        csv_path: Ruta del archivo CSV de entrada
        xlsx_path: Ruta del archivo XLSX de salida
        delimiter: Delimitador usado en el CSV (por defecto ',')
        encoding: Codificación del archivo CSV (si es None, se detecta automáticamente)
    """
    if encoding is None:
        encoding = detect_encoding(csv_path)

    wb = Workbook()
    ws = wb.active

    with open(csv_path, 'r', encoding=encoding) as csv_file:
        reader = csv.reader(csv_file, delimiter=delimiter)
        for row in reader:
            ws.append(row)

    wb.save(xlsx_path)
