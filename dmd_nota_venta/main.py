import os
import sys

# Add parent directory to path to import common module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openpyxl
import common.config as config
from datetime import datetime
import csv
import codecs
import common.db as db
import common.excel as excel_utils
import traceback



class FileFormatError(Exception):
    pass
#
# Busco Novedades archivos nuevos
#
def read_files(path):
    current_time = datetime.now()
    file_list = []
    for file in  os.listdir(path):
        file_path = os.path.join(path, file)
        created_time = datetime.fromtimestamp(os.path.getctime(file_path))
        time_difference = current_time - created_time
        # Solo para los archivos que fueron creados hace mas de un minuto, 
        # para evitar tomar un archivo que se esta creando

        if os.path.isfile(file_path) and (file.endswith('.xlsx') or file.endswith('.csv')) and time_difference.total_seconds() >= 10:
            file_list.append(file_path)
    return file_list
#
# Leo master relacion combo sku con varios sku y sus cantidades
#
def read_master(file_path):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active

    column_data = []
    for id, row in enumerate(zip(sheet['A'],  # SKU_COMBO
                   sheet['C'], #cantidad
                   sheet['D'],  #SKU
                   sheet['B'] # Descripcion
                   
                   )):
        reg = {}
        reg['sku_combo'] = row[0].value
        reg['sku'] = row[2].value
        reg['cantidad'] = row[1].value
        reg['descripcion'] = row[3].value
        if reg['sku'] is not None and id >0:
            column_data.append(reg)

    return column_data


def existe_en_combos(combos, sku):
    for combo in combos:
        if combo['sku'] == sku:
            return True
    return False

def actualizar_items(combos, sku, item):
    for combo in combos:
        if combo['sku'] == sku:
            combo['items'] =item
#
# Busco el sku en el master
#       Si es un combo recorro y retorno un array con la relacion sku, cantidad del combo * cantidad solicitada
#       Si no es un combo solo retorno un array con el mismo sku de entrada y su cantidad.
#
def buscar_en_master(sku_pair, cantidad, numero_factura):
    combo_pairs = []
    items = 0
    item_combo={}
    for i, m in enumerate(masters):
        if m['sku_combo'] == str(sku_pair['sku']):
            items += 1
            rec={}
            rec['sku'] = m['sku']
            rec['cantidad'] = m['cantidad'] * cantidad
            rec['descripcion'] = m['descripcion']
            if "REG" in sku_pair['sku'] :
                
                item_combo['numero_factura'] = numero_factura    
                item_combo["sku"] = m['sku_combo']
                item_combo["cantidad"] =  cantidad if isinstance(cantidad, (int, float, complex)) else 0
                item_combo["items"] = items
                    
            combo_pairs.append( rec)

    if "REG" in str(sku_pair['sku'] ):
        if len(item_combo) == 0:
            item_combo['numero_factura'] = numero_factura    
            item_combo['sku'] = sku_pair['sku']
            item_combo['cantidad'] = cantidad if isinstance(cantidad, (int, float, complex))  else 0
            item_combo['items'] = 0
        combos.append(item_combo)
       
    if len(combo_pairs) == 0:
        rec={}
        rec['sku'] = sku_pair['sku']
        rec['cantidad'] =cantidad
        rec['descripcion'] = sku_pair['descripcion']
        return [rec]
    else:
        
        return combo_pairs
    
#
# Por cada archivo en el xlsx o csv, se combierte a formato Valkimia
#
def read_excel_columns(file_path):

    row_con_datos = 2
    column_data = []

    ## A                B       C           D       E           F   G           H           I       J       K       L       M       N                   O           P       Q
    #> 0                1       2           3       4           5   6           7           8       9       10      11      12      13                  14          15  16
    ## 1	            2	    3	        4	    5	        6	7	        8	        9	    10	    11	    12	    13	    14	                15	        16	17
    ## Nro Documento	Fecha	cliente ID	Nombre	Codigo Art	FP	Descripci?n	cantidad	Lote	Obs1	Obs2	Obs3	Obs4	Direcci¢n Entrega	Localidad	CP	Provincia

    # Detectar extensión del archivo
    extension = os.path.splitext(file_path)[1].lower()

    if extension == '.xlsx':
        rows = _read_xlsx_rows(file_path)
    elif extension == '.csv':
        rows = _read_csv_rows(file_path)
    else:
        raise FileFormatError(f'Extensión no soportada: {extension}')

    for id, row in enumerate(rows):
        if id >= row_con_datos:
            reg = {}
            reg['documento'] = row[0]
            reg['numero_factura']= reg['documento']
            reg['fecha'] = row[1]
            reg['cliente_id'] = row[2]
            reg['nombre'] = row[3]
            sku = row[4]
            reg['sku'] = sku.upper() if isinstance(sku, str) else sku
            reg['fp'] = row[5]
            reg['descripcion'] = row[6]
            reg['cantidad'] = _parse_number(row[7])
            reg['lote'] = row[8]

            obs1 = '' if row[9] is None else row[9]
            obs2 = '' if row[10] is None else row[10]
            obs3 = '' if row[11] is None else row[11]
            obs4 = '' if row[12] is None else row[12]
            reg['observacion'] = f"{obs1} {obs2} {obs3} {obs4}".strip()
            reg['direccion'] = row[13]
            reg['ciudad'] = row[14]
            reg['codigo_postal'] = row[15]
            reg['provincia'] = row[16]
            #print(f"type: {type(reg['sku'])} valor: {reg['sku']}")
            if id == 0 and not reg['nombre'].upper() == 'Razon Social'.upper():
                raise FileFormatError('error de formato')
            if reg['sku'] is not None and id >0:
                lista = buscar_en_master({'sku': reg['sku'], 'descripcion': reg['descripcion']}, reg['cantidad'], reg['numero_factura'])
                for l in lista:

                    reg2 = dict(reg)
                    reg2['sku'] = l['sku']
                    reg2['cantidad'] = l['cantidad']
                    reg2['descripcion'] = l['descripcion']
                    column_data.append(reg2)


    return column_data


def _read_xlsx_rows(file_path):
    """Lee filas de un archivo XLSX y retorna lista de tuplas con valores."""
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    rows = []
    for row in zip(sheet['A'], sheet['B'], sheet['C'], sheet['D'], sheet['E'],
                   sheet['F'], sheet['G'], sheet['H'], sheet['I'], sheet['J'],
                   sheet['K'], sheet['L'], sheet['M'], sheet['N'], sheet['O'],
                   sheet['P'], sheet['Q']):
        rows.append(tuple(cell.value for cell in row))
    return rows


def _read_csv_rows(file_path):
    """Lee filas de un archivo CSV y retorna lista de tuplas con valores."""
    encoding = excel_utils.detect_encoding(file_path)
    rows = []
    with open(file_path, 'r', encoding=encoding) as csv_file:
        reader = csv.reader(csv_file, delimiter=';')
        for row in reader:
            # Asegurar que la fila tenga 17 columnas (A-Q)
            while len(row) < 17:
                row.append(None)
            # Convertir strings vacíos a None
            row = [val if val != '' else None for val in row]
            rows.append(tuple(row))
    return rows


def _parse_number(value):
    """Convierte un valor a número si es posible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

def move_to_processed(file_path):
    filename = os.path.basename(file_path)
    
    try:
        os.rename(file_path, f'{cnf.processed_path}\{filename}')
    except FileExistsError:
        os.remove(f'{cnf.processed_path}\{filename}')
        os.rename(file_path, f'{cnf.processed_path}\{filename}')
    


def customer_array_management( cliente_id,  nombre, direccion, ciudad, codigo_postal, tipo, documento, observacion, provincia):
    encontrado = False
    for c in new_customers:
        if (cliente_id == c['cliente_id']):
            encontrado = True
            break
    
    if not encontrado:
        new_customers.append({'cliente_id': cliente_id,
                            'nombre': nombre,
                            'direccion': direccion,
                            'localidad': ciudad,
                            'codigo_postal': codigo_postal,
                            'tipo': tipo,
                            'numero_documento': documento,
                            'observacion': observacion,
                            'provincia': provincia}
                            )
def write_combos(combos_a_guardar):
    f=cnf.combos_path
    salida = f"{f}\combos.csv"
    archivo_existia = os.path.exists(salida)
    with codecs.open(salida, 'a','utf8') as archivo_csv:
        writer = csv.writer(archivo_csv, delimiter=';')
        if not archivo_existia:
            titulo = [ 'Archivo', 'Factura', 'Fecha', 'Combo SKU', 'Cantidad Solicitada', 'Cantidad de Articulos']
            writer.writerow(titulo)
        for fila in combos_a_guardar:
            writer.writerow((fila['file'], fila['numero_factura'], fila['fecha'],fila['sku'],fila['cantidad'],fila['items']))

def write_csv(f):
    try: 
        excel = read_excel_columns(f)
        
        filename = os.path.basename(f)
        
        salida = f"{cnf.import_path}\{os.path.splitext(filename)[0]}.csv"
        with codecs.open(salida, 'w','utf8') as archivo_csv:
            writer = csv.writer(archivo_csv, delimiter=';')
            titulo = [ 'Nro Documento',
                    'Fecha',
                    'cliente ID',
                    'Nombre',
                    'Codigo Art',
                    'FP',
                    'Descripción',
                    'cantidad',
                    'Lote',
                    'Obs1',
                    'Obs2',
                    'Obs3',
                    'Obs4',
                    'Dirección',
                    'Localidad']
            writer.writerow(titulo)
            for fila in excel:
                entidad_id = None
                entidad_id = db.getENT(fila['cliente_id'], fila['provincia'],
                                    fila['codigo_postal'], fila['direccion'], fila['observacion'], fila['nombre'])
                
                if entidad_id is None:
                    fila['tipo'] = 'DNI'
                    customer_array_management(fila['cliente_id'],
                                            fila['nombre'],
                                            fila['direccion'],
                                            fila['ciudad'],
                                            fila['codigo_postal'],
                                            fila['tipo'] if fila['tipo'] is not None else '',
                                            fila['cliente_id'],
                                            fila['observacion'] if fila['observacion'] is not None else '',
                                            fila['provincia']
                                            )
                    # new_customers.append({'cliente_id': fila['documento'],
                    #                     'nombre': fila['nombre'],
                    #                     'direccion': fila['direccion'],
                    #                     'localidad': fila['ciudad'],
                    #                     'codigo_postal': '1',
                    #                     'tipo': fila['tipo'],
                    #                     'numero_documento': fila['documento']})
                
                r = [fila['numero_factura'],    #1
                    fila['fecha'],            #2
                    fila['cliente_id'] ,       #3
                    fila['nombre'],            #4
                    fila['sku'],               #5
                    '1',                       #6
                    '',                        #7
                    fila['cantidad'],          #8
                    '',
                    fila['observacion'],
                    '',
                    '',
                    '',
                    fila['direccion'],
                    fila['provincia']
                    ]
                writer.writerow(r)
        return f, fila['fecha'] 
    except FileFormatError as e:
        raise e
    except Exception as e:
        raise e
    
def write_new_customers(data, f):
    filename = os.path.basename(f)
    salida = f"{cnf.new_customer_path}/new_customer_{os.path.splitext(filename)[0]}.csv"
    with codecs.open(salida, 'w','utf-8') as archivo_csv:
        writer = csv.writer(archivo_csv, delimiter=';')
        titulo=[1,2,3,4,5,6,7]
      
        writer.writerow(titulo)
        for d in data:
            r= [d['cliente_id'],
                d['nombre'],
                d['direccion'],
                d['localidad'],
                d['codigo_postal'],
                d['tipo'],
                d['numero_documento']
                ]
            
            writer.writerow(r)

            db.generate_insert_query(d)
        
def procesa_combos(file, fecha):
    
    for c in combos:
        registros={}
        registros['archivo'] = file
        registros['documento'] = c['numero_factura']
        registros['fecha'] = fecha
        registros['sku'] = c['sku']
        registros['cantidad'] = c['cantidad']
        registros['items'] = c['items']
        combos_a_guardar.append(registros)
    return combos_a_guardar



def formatear_fecha(fecha):
    # Si es un objeto datetime
    if isinstance(fecha, datetime):
        return fecha.strftime('%Y-%m-%d')
    # Si es un string
    elif isinstance(fecha, str):
        try:
            # Intentar convertir el string a datetime (asumiendo que está en formato dd/mm/yyyy)
            fecha_dt = datetime.strptime(fecha, '%d/%m/%Y')
            return fecha_dt.strftime('%Y-%m-%d')
        except ValueError:
            # Manejar error si el string no está en el formato esperado
            raise ValueError(f"Formato de fecha no reconocido: {fecha}")
    else:
        return ""



timestamp_inicio = datetime.now()
print(f"Inicio del proceso: {timestamp_inicio}")

# Cargar configuración con el .env del directorio del script
env_file = os.path.join(os.path.dirname(__file__), '.env')
cnf = config.Config(env_path=env_file)
combos=[]
combos_a_guardar = []
try:
    masters = read_master(cnf.master)
    
    files = read_files(cnf.getPath())

    db = db.DB()
    
    for i, f in enumerate(files):
        new_customers = []
        try:
            combos=[]
            file=""
            numero_factura=""
            fecha=""
            print (f"Procesando archivo: {f}")
            file, fecha = write_csv(f)
            if len(new_customers) > 0:
                write_new_customers(new_customers, f)
            
            combos_a_guardar = procesa_combos(os.path.basename(file), formatear_fecha(fecha))
            #print(f"Guardando combos {combos_a_guardar}")
            
            move_to_processed(f)
        except FileFormatError as e:
            print(f"ERROR: procesando archivo {f} es un problema {e}")
            continue
        except Exception as e:
            
            print(traceback.format_exc())
            
            print(e)

    if len(combos_a_guardar)    > 0:
       print(f"Guardando combos {combos_a_guardar}")
       db.insert_archivo(combos_a_guardar)
       #write_combos(combos_a_guardar)

except Exception as e:
    print(traceback.format_exc())
    print(e)                
timestamp_fin = datetime.now()
time_diff = (timestamp_fin - timestamp_inicio)
print(f"Fin del proceso: {timestamp_fin} {time_diff}")
