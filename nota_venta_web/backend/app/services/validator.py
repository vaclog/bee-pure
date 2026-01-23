"""
Validador dinámico de archivos Excel según configuración del cliente
"""
import openpyxl
from typing import List, Dict, Any, Tuple
from app.models import ConfiguracionCliente
from app.schemas.archivo import ErrorValidacion, WarningValidacion, EstadisticasPreview


class FileValidator:
    """Valida archivos Excel según configuración del cliente"""

    def __init__(self, configuracion: ConfiguracionCliente):
        self.config = configuracion
        self.mapeo = configuracion.mapeo_excel
        self.columnas = self.mapeo.get("columnas", {})
        self.header_row = self.mapeo.get("header_row", 1)
        self.data_start_row = self.mapeo.get("data_start_row", 2)
        self.validacion_header = self.mapeo.get("validacion_header")

    def validate(self, file_path: str) -> Dict[str, Any]:
        """
        Valida un archivo Excel

        Returns:
            Dict con: valido, errores, warnings, preview, estadisticas
        """
        errores: List[ErrorValidacion] = []
        warnings: List[WarningValidacion] = []

        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active

            # 1. Validar que existan las columnas esperadas
            errores_columnas = self._validar_columnas(sheet)
            errores.extend(errores_columnas)

            # 2. Validar header
            if self.validacion_header:
                error_header = self._validar_header(sheet)
                if error_header:
                    errores.append(error_header)

            # 3. Validar datos fila por fila
            errores_datos, warnings_datos, datos_preview, stats = self._validar_datos(sheet)
            errores.extend(errores_datos)
            warnings.extend(warnings_datos)

            workbook.close()

            return {
                "valido": len(errores) == 0,
                "errores": [e.model_dump() for e in errores],
                "warnings": [w.model_dump() for w in warnings],
                "preview": datos_preview,
                "estadisticas": stats.model_dump() if stats else None
            }

        except Exception as e:
            return {
                "valido": False,
                "errores": [{
                    "tipo": "error_lectura",
                    "mensaje": f"Error al leer el archivo: {str(e)}"
                }],
                "warnings": [],
                "preview": [],
                "estadisticas": None
            }

    def _validar_columnas(self, sheet) -> List[ErrorValidacion]:
        """Valida que existan todas las columnas esperadas"""
        errores = []

        for nombre_campo, letra_columna in self.columnas.items():
            # Si es una lista de columnas (ej: observaciones)
            if isinstance(letra_columna, list):
                for letra in letra_columna:
                    if not self._column_exists(sheet, letra):
                        errores.append(ErrorValidacion(
                            tipo="columna_faltante",
                            columna=letra,
                            mensaje=f"Columna {letra} ({nombre_campo}) no encontrada"
                        ))
            else:
                if not self._column_exists(sheet, letra_columna):
                    errores.append(ErrorValidacion(
                        tipo="columna_faltante",
                        columna=letra_columna,
                        mensaje=f"Columna {letra_columna} ({nombre_campo}) no encontrada"
                    ))

        return errores

    def _column_exists(self, sheet, column_letter: str) -> bool:
        """Verifica si una columna existe"""
        try:
            cell = sheet[f"{column_letter}1"]
            return True
        except:
            return False

    def _validar_header(self, sheet) -> ErrorValidacion | None:
        """Valida el header del archivo"""
        try:
            # Buscar la celda que debe contener el header de validación
            header_col = self.columnas.get("nombre", "A")
            header_cell = sheet[f"{header_col}{self.header_row}"]
            header_value = header_cell.value

            if header_value is None:
                return ErrorValidacion(
                    fila=self.header_row,
                    tipo="header_vacio",
                    mensaje=f"Header vacío en fila {self.header_row}"
                )

            if self.validacion_header.upper() not in str(header_value).upper():
                return ErrorValidacion(
                    fila=self.header_row,
                    tipo="header_invalido",
                    mensaje=f"Header esperado '{self.validacion_header}', encontrado '{header_value}'"
                )

            return None

        except Exception as e:
            return ErrorValidacion(
                fila=self.header_row,
                tipo="error_header",
                mensaje=f"Error al validar header: {str(e)}"
            )

    def _validar_datos(self, sheet) -> Tuple[List[ErrorValidacion], List[WarningValidacion], List[Dict], EstadisticasPreview]:
        """Valida los datos del archivo"""
        errores = []
        warnings = []
        preview_data = []
        clientes_nuevos_set = set()
        combos_set = set()
        skus_set = set()

        total_filas = 0
        max_preview = 10

        for idx, row in enumerate(sheet.iter_rows(min_row=self.data_start_row), start=self.data_start_row):
            try:
                # Extraer datos de la fila
                datos_fila = self._extraer_datos_fila(row)

                # Skip filas vacías
                if not datos_fila.get("sku"):
                    continue

                total_filas += 1

                # Validar campos requeridos
                errores_fila = self._validar_campos_requeridos(datos_fila, idx)
                errores.extend(errores_fila)

                # Detectar combos (SKUs que contienen "REG")
                sku = str(datos_fila.get("sku", ""))
                if "REG" in sku.upper():
                    combos_set.add(sku)

                skus_set.add(sku)

                # Agregar a preview (solo primeras 10 filas)
                if len(preview_data) < max_preview:
                    preview_data.append({
                        "fila": idx,
                        **datos_fila
                    })

            except Exception as e:
                errores.append(ErrorValidacion(
                    fila=idx,
                    tipo="error_lectura_fila",
                    mensaje=f"Error al leer fila: {str(e)}"
                ))

        # Estadísticas
        stats = EstadisticasPreview(
            total_filas=total_filas,
            clientes_nuevos=0,  # Se calculará en procesamiento real
            combos_detectados=len(combos_set),
            skus_unicos=len(skus_set)
        )

        return errores, warnings, preview_data, stats

    def _extraer_datos_fila(self, row) -> Dict[str, Any]:
        """Extrae datos de una fila según el mapeo de columnas"""
        datos = {}

        for nombre_campo, letra_columna in self.columnas.items():
            if isinstance(letra_columna, list):
                # Campos múltiples (ej: observaciones)
                valores = []
                for letra in letra_columna:
                    col_idx = openpyxl.utils.column_index_from_string(letra) - 1
                    if col_idx < len(row):
                        valor = row[col_idx].value
                        if valor:
                            valores.append(str(valor))
                datos[nombre_campo] = " ".join(valores).strip() if valores else None
            else:
                # Campo simple
                col_idx = openpyxl.utils.column_index_from_string(letra_columna) - 1
                if col_idx < len(row):
                    datos[nombre_campo] = row[col_idx].value

        return datos

    def _validar_campos_requeridos(self, datos: Dict, fila: int) -> List[ErrorValidacion]:
        """Valida que los campos requeridos no estén vacíos"""
        errores = []
        campos_requeridos = ["sku", "cantidad", "fecha", "numero_factura"]

        for campo in campos_requeridos:
            if not datos.get(campo):
                errores.append(ErrorValidacion(
                    fila=fila,
                    columna=campo,
                    tipo="campo_requerido",
                    mensaje=f"Campo '{campo}' es requerido y está vacío"
                ))

        # Validar que cantidad sea numérica
        cantidad = datos.get("cantidad")
        if cantidad and not isinstance(cantidad, (int, float)):
            try:
                float(cantidad)
            except (ValueError, TypeError):
                errores.append(ErrorValidacion(
                    fila=fila,
                    columna="cantidad",
                    tipo="tipo_invalido",
                    mensaje=f"Cantidad debe ser numérica, encontrado '{cantidad}'"
                ))

        return errores
