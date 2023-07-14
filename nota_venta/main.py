import os
import openpyxl
import config
from datetime import datetime
import csv
import codecs
import db
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
                   sheet['M'], #cantidad
                   sheet['N'],  #SKU
                   sheet['O'] # Descripcion
                   
                   )):
        reg = {}
        reg['sku_combo'] = row[0].value
        reg['sku'] = row[2].value
        reg['cantidad'] = row[1].value
        reg['descripcion'] = row[3].value
        if reg['sku'] is not None and id >0:
            column_data.append(reg)

    return column_data

#
# Busco el sku en el master
#       Si es un combo recorro y retorno un array con la relacion sku, cantidad del combo * cantidad solicitada
#       Si no es un combo solo retorno un array con el mismo sku de entrada y su cantidad.
#
def buscar_en_master(sku_pair, cantidad):
    combo_pairs = []
    for i, m in enumerate(masters):
        if m['sku_combo'] == sku_pair['sku']:
            rec={}
            rec['sku'] = m['sku']
            rec['cantidad'] = m['cantidad'] * cantidad
            rec['descripcion'] = m['descripcion']
            combo_pairs.append( rec)

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

    column_data = []
    for id, row in enumerate(zip(sheet['A'],  # Nombre
                   sheet['C'],  #Documento
                   sheet['E'],  #Provincia
                   sheet['F'],  #Ciudad 
                   sheet['G'],  #Direccion
                   sheet['J'],  #Fecha
                   sheet['P'],  #Numero Factura
                   sheet['U'],  #SKU
                   sheet['V'], # Descripcion
                   sheet['W'],  #Cantidad
                   sheet['B'], # Tipo
                   sheet['AB'], # Observacion
                   sheet['H']  # CP
                   )):
        reg = {}
        reg['nombre'] = row[0].value
        reg['documento'] = row[1].value
        reg['provincia'] = row[2].value
        reg['ciudad'] = row[3].value
        reg['direccion'] = row[4].value
        reg['fecha'] = row[5].value
        reg['numero_factura'] = row[6].value
        reg['sku'] = row[7].value
        reg['descripcion'] = row[8].value
        reg['cantidad'] = row[9].value
        reg['tipo'] = row[10].value
        reg['observacion'] = row[11].value
        reg['codigo_postal'] = row[12].value
        #print(f"type: {type(reg['sku'])} valor: {reg['sku']}")
        if id == 0 and not reg['nombre'] == 'Razon Social':
            raise FileFormatError('error de formato')
        if reg['sku'] is not None and id >0:
            lista = buscar_en_master({'sku': reg['sku'], 'descripcion': reg['descripcion']}, reg['cantidad'])
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
    


def customer_array_management( cliente_id,  nombre, direccion, ciudad, codigo_postal, tipo, documento):
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
                            'numero_documento': documento})
            
def write_csv(f):
    excel = read_excel_columns(f)
     
    filename = os.path.basename(f)
    
    salida = f"{cnf.import_path}\{os.path.splitext(filename)[0]}.csv"
    with codecs.open(salida, 'w','ansi') as archivo_csv:
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
                                   fila['codigo_postal'], fila['direccion'])
            
            if entidad_id is None:
                
                customer_array_management(fila['documento'],
                                          fila['nombre'],
                                          fila['direccion'],
                                          fila['ciudad'],
                                          fila['codigo_postal'],
                                          fila['tipo'],
                                          fila['documento']
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
                 '',
                 ''
                 ]
            writer.writerow(r)
    
def write_new_customers(data, f):
    filename = os.path.basename(f)
    salida = f"{cnf.new_customer_path}\\new_customer_{os.path.splitext(filename)[0]}.csv"
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
        
timestamp_inicio = datetime.now()
print(f"Inicio del proceso: {timestamp_inicio}")

cnf = config.Config()
try:
    masters = read_master(cnf.master)
    
    files = read_files(cnf.getPath())

    db = db.DB()

    for i, f in enumerate(files):
        new_customers = []
        try:
            print (f"Procesando archivo: {f}")
            write_csv(f)
            if len(new_customers) > 0:
                write_new_customers(new_customers, f)
                
            move_to_processed(f)
        except FileFormatError as e:
            print(f"ERROR: procesando archivo {f} es un problema {e}")
            continue
        except Exception as e:
            
            print(traceback.format_exc())
            
            print(e)
            

except Exception as e:
    print(traceback.format_exc())
    print(e)                
timestamp_fin = datetime.now()
time_diff = (timestamp_fin - timestamp_inicio)
print(f"Fin del proceso: {timestamp_fin} {time_diff}")