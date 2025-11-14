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
        if os.path.isfile(file_path) and file.endswith('.xlsx') and time_difference.total_seconds() >= 60:            
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
# Por cada archivo en el xlsx, se combierte a formato Valkimia
#
def read_excel_columns(file_path):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    row_con_datos = 2
    column_data = []
    for id, row in enumerate(zip(sheet['D'],  # Nombre Row 1
                   sheet['A'],  #Documento Row 2
                   sheet['O'],  #Provincia Row 3
                   sheet['O'],  #Ciudad  Row 4
                   sheet['N'],  #Direccion Row 5
                   sheet['B'],  #Fecha Row 6
                   sheet['A'],  #Numero Factura Row 7
                   sheet['E'],  #SKU Row 8
                   sheet['G'], # Descripcion Row 9
                   sheet['H'],  #Cantidad Row 10
                   sheet['D'], # Tipo Row 11
                   sheet['J'], # Observacion1 Row 12,
                   sheet['K'], # Observacion2 Row 13,
                   sheet['L'], # Observacion3 Row 14,
                   sheet['M'], # Observacion4 Row 15,
                   sheet['P'],  # CP Row 16
                   sheet['Q']   # FP Row 17
                   )):
        if id >= row_con_datos:
            reg = {}
            reg['nombre'] = row[0].value
            reg['documento'] = row[1].value
            reg['provincia'] = row[16].value
            reg['ciudad'] = row[3].value
            reg['direccion'] = row[4].value
            reg['fecha'] = row[5].value
            reg['numero_factura'] = row[6].value
            reg['sku'] = row[7].value
            reg['descripcion'] = row[8].value
            reg['cantidad'] = row[9].value
            reg['tipo'] = row[10].value
            obs1 = '' if row[11].value is None else row[11].value
            obs2 = '' if row[12].value is None else row[12].value
            obs3 = '' if row[13].value is None else row[13].value
            obs4 = '' if row[14].value is None else row[14].value
            reg['observacion'] = f"{obs1} {obs2} {obs3} {obs4}".strip()
            reg['codigo_postal'] = row[15].value
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
            entidad_id = db.getENT(fila['documento'], fila['provincia'],
                                   fila['codigo_postal'], fila['direccion'], fila['observacion'])
            
            if entidad_id is None:
                if fila['tipo']!='DNI':
                    fila['tipo']='DNI'
                customer_array_management(fila['documento'],
                                          fila['nombre'],
                                          fila['direccion'],
                                          fila['ciudad'],
                                          fila['codigo_postal'],
                                          fila['tipo'] if fila['tipo'] is not None else '',
                                          fila['documento'],
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
                  fila['documento'] ,       #3
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
    
def write_new_customers(data, f):
    filename = os.path.basename(f)
    salida = f"{cnf.new_customer_path}/new_customer_{os.path.splitext(filename)[0]}.csv"
    with codecs.open(salida, 'w','ansi') as archivo_csv:
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
