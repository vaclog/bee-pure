import os
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
    """Scans directory for new Excel files ready for processing.
    
    Args:
        path (str): Directory path to scan for files
        
    Returns:
        list: List of file paths that are .xlsx files created more than 1 minute ago
    """
    try:
        if not os.path.exists(path):
            print(f"ERROR: Directory does not exist: {path}")
            return []
            
        current_time = datetime.now()
        file_list = []
        
        for file in os.listdir(path):
            try:
                file_path = os.path.join(path, file)
                created_time = datetime.fromtimestamp(os.path.getctime(file_path))
                time_difference = current_time - created_time
                # Solo para los archivos que fueron creados hace mas de un minuto, 
                # para evitar tomar un archivo que se esta creando
                if os.path.isfile(file_path) and file.endswith('.xlsx') and time_difference.total_seconds() >= 60:            
                    file_list.append(file_path)
            except (OSError, IOError) as e:
                print(f"ERROR: Cannot access file {file}: {e}")
                continue
                
        return file_list
        
    except PermissionError as e:
        print(f"ERROR: Permission denied accessing directory {path}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error reading directory {path}: {e}")
        print(traceback.format_exc())
        return []
#
# Leo master relacion combo sku con varios sku y sus cantidades
#
def read_master(file_path):
    """Reads master Excel file containing combo SKU mappings.
    
    Args:
        file_path (str): Path to master Excel file
        
    Returns:
        list: List of dictionaries with combo mappings (sku_combo, sku, cantidad, descripcion)
    """
    try:
        if not os.path.exists(file_path):
            print(f"ERROR: Master file does not exist: {file_path}")
            return []
            
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        column_data = []
        for id, row in enumerate(zip(sheet['A'],  # SKU_COMBO
                       sheet['M'], #cantidad
                       sheet['N'],  #SKU
                       sheet['O'] # Descripcion
                       )):
            try:
                reg = {}
                reg['sku_combo'] = row[0].value
                reg['sku'] = row[2].value
                reg['cantidad'] = row[1].value
                reg['descripcion'] = row[3].value
                if reg['sku'] is not None and id > 0:
                    column_data.append(reg)
            except Exception as e:
                print(f"ERROR: Processing row {id} in master file: {e}")
                continue

        return column_data
        
    except openpyxl.utils.exceptions.InvalidFileException as e:
        print(f"ERROR: Invalid Excel file format {file_path}: {e}")
        return []
    except PermissionError as e:
        print(f"ERROR: Permission denied reading master file {file_path}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error reading master file {file_path}: {e}")
        print(traceback.format_exc())
        return []


def existe_en_combos(combos, sku):
    """Checks if a SKU exists in the combos list.
    
    Args:
        combos (list): List of combo dictionaries
        sku (str): SKU to search for
        
    Returns:
        bool: True if SKU exists in combos, False otherwise
    """
    for combo in combos:
        if combo['sku'] == sku:
            return True
    return False

def actualizar_items(combos, sku, item):
    """Updates items count for a specific SKU in combos list.
    
    Args:
        combos (list): List of combo dictionaries
        sku (str): SKU to update
        item (int): New items count
    """
    for combo in combos:
        if combo['sku'] == sku:
            combo['items'] =item
#
# Busco el sku en el master
#       Si es un combo recorro y retorno un array con la relacion sku, cantidad del combo * cantidad solicitada
#       Si no es un combo solo retorno un array con el mismo sku de entrada y su cantidad.
#
def buscar_en_master(sku_pair, cantidad, numero_factura):
    """Searches for SKU in master list and expands combos if found.
    
    If SKU is a combo, returns list of individual items with calculated quantities.
    If not a combo, returns the original SKU with its quantity.
    
    Args:
        sku_pair (dict): Dictionary with 'sku' and 'descripcion' keys
        cantidad (int/float): Quantity requested
        numero_factura (str): Invoice number for tracking
        
    Returns:
        list: List of dictionaries with expanded SKUs and quantities
    """
    combo_pairs = []
    items = 0
    item_combo={}
    for m in masters:
        if m['sku_combo'] == sku_pair['sku']:
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

    if "REG" in sku_pair['sku'] :
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
    """Reads Excel file and converts it to Valkimia format.
    
    Processes each row of the Excel file, validates format, and expands combo SKUs.
    
    Args:
        file_path (str): Path to Excel file to process
        
    Returns:
        list: List of dictionaries with processed order data
        
    Raises:
        FileFormatError: If file doesn't have expected header format
    """
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
        reg['provincia'] = row[2].value.upper()
        reg['ciudad'] = row[3].value.upper()
        reg['direccion'] = row[4].value.upper()
        reg['fecha'] = row[5].value
        reg['numero_factura'] = row[6].value
        reg['sku'] = row[7].value
        reg['descripcion'] = row[8].value
        reg['cantidad'] = row[9].value
        reg['tipo'] = row[10].value
        reg['observacion'] = row[11].value
        reg['codigo_postal'] = row[12].value
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
    """Moves processed file to the processed directory.
    
    Args:
        file_path (str): Path to file to move
    """
    try:
        filename = os.path.basename(file_path)
        destination = f'{cnf.processed_path}\{filename}'
        
        if not os.path.exists(cnf.processed_path):
            os.makedirs(cnf.processed_path)
            
        os.rename(file_path, destination)
        print(f"File moved to processed: {filename}")
        
    except FileExistsError:
        try:
            os.remove(destination)
            os.rename(file_path, destination)
            print(f"File replaced in processed directory: {filename}")
        except (OSError, IOError) as e:
            print(f"ERROR: Cannot replace existing file {destination}: {e}")
    except PermissionError as e:
        print(f"ERROR: Permission denied moving file {file_path}: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error moving file {file_path}: {e}")
        print(traceback.format_exc())
    


def customer_array_management( cliente_id,  nombre, direccion, ciudad, codigo_postal, tipo, documento, observacion, provincia):
    """Manages new customer array by adding unique customers.
    
    Args:
        cliente_id (str): Customer ID
        nombre (str): Customer name
        direccion (str): Customer address
        ciudad (str): Customer city
        codigo_postal (str): Postal code
        tipo (str): Customer type
        documento (str): Document number
        observacion (str): Observations
        provincia (str): Province
    """
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
    """Writes combo data to CSV file.
    
    Args:
        combos_a_guardar (list): List of combo dictionaries to save
    """
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
    """Converts Excel file to CSV format for Valkimia import.
    
    Args:
        f (str): Path to Excel file
        
    Returns:
        tuple: (file_path, fecha) - processed file path and date
    """
    try:
        excel = read_excel_columns(f)
        
        if not excel:
            print(f"WARNING: No data found in Excel file: {f}")
            return f, None
         
        filename = os.path.basename(f)
        
        if not os.path.exists(cnf.import_path):
            os.makedirs(cnf.import_path)
            
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
                 '',
                 ''
                 ]
            writer.writerow(r)
        
        print(f"CSV file created: {salida}")
        return f, fila['fecha'] if 'fila' in locals() and fila else None
        
    except Exception as e:
        print(f"ERROR: Failed to write CSV file for {f}: {e}")
        print(traceback.format_exc())
        return f, None 
    
def write_new_customers(data, f):
    """Writes new customer data to CSV file and database.
    
    Args:
        data (list): List of new customer dictionaries
        f (str): Original file path for naming output file
    """
    try:
        if not data:
            print("WARNING: No new customer data to write")
            return
            
        filename = os.path.basename(f)
        
        if not os.path.exists(cnf.new_customer_path):
            os.makedirs(cnf.new_customer_path)
            
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

                try:
                    db.generate_insert_query(d)
                except Exception as e:
                    print(f"ERROR: Failed to insert customer {d.get('cliente_id', 'unknown')}: {e}")
                
            print(f"New customers file created: {salida}")
        
    except Exception as e:
        print(f"ERROR: Failed to write new customers file for {f}: {e}")
        print(traceback.format_exc())
        
def procesa_combos(file, fecha):
    """Processes combo data for database insertion.
    
    Args:
        file (str): Source file name
        fecha (str): Processing date
        
    Returns:
        list: List of combo records ready for database insertion
    """
    
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
    """Formats date to YYYY-MM-DD format.
    
    Args:
        fecha (datetime/str): Date to format
        
    Returns:
        str: Formatted date string or empty string if invalid
        
    Raises:
        ValueError: If string date format is not recognized
    """
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

cnf = config.Config()
combos=[]
combos_a_guardar = []
try:
    print("Loading master file...")
    masters = read_master(cnf.master)
    if not masters:
        print("ERROR: No master data loaded. Exiting.")
        exit(1)
    print(f"Loaded {len(masters)} master records")
    
    print("Scanning for files to process...")
    files = read_files(cnf.getPath())
    if not files:
        print("No files found to process.")
        exit(0)
    print(f"Found {len(files)} files to process")

    print("Connecting to database...")
    try:
        db = db.DB()
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        print("Continuing without database operations...")
        db = None
    
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
            
            if fecha:
                combos_a_guardar = procesa_combos(os.path.basename(file), formatear_fecha(fecha))
            else:
                print(f"WARNING: No date found for file {f}, skipping combo processing")
            
            move_to_processed(f)
            print(f"Successfully processed: {f}")
        except FileFormatError as e:
            print(f"ERROR: procesando archivo {f} es un problema {e}")
            continue
        except Exception as e:
            
            print(traceback.format_exc())
            
            print(e)

    if len(combos_a_guardar) > 0 and db is not None:
        print(f"Saving {len(combos_a_guardar)} combo records to database")
        try:
            db.insert_archivo(combos_a_guardar)
            print("Combo records saved successfully")
        except Exception as e:
            print(f"ERROR: Failed to save combo records: {e}")
            print(traceback.format_exc())
    elif len(combos_a_guardar) > 0 and db is None:
        print("WARNING: Cannot save combos - no database connection")
    else:
        print("No combo records to save")

except Exception as e:
    print(traceback.format_exc())
    print(e)                
timestamp_fin = datetime.now()
time_diff = (timestamp_fin - timestamp_inicio)
print(f"Fin del proceso: {timestamp_fin} {time_diff}")