import pymssql
import os
from dotenv import load_dotenv
from datetime import datetime
import re
# Cargar variables desde el archivo .env
load_dotenv()

import traceback
class DB:
    def __init__(self):
        self.server = os.getenv('DB_HOST')
        self.db = os.getenv('DB_NAME')
        self.user = os.getenv('DB_USER')
        self.password  = os.getenv('DB_PASSWORD')
        try:
            self.conn = pymssql.connect(self.server, 
                                   self.user, 
                                   self.password, 
                                   self.db)		
            print ('CONECTADO')
            self.cursor = self.conn.cursor(as_dict=True)
        
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            
    def getENT(self, entidad_externa, provincia, cp, direccion, obs):

        if (obs == None):
            obs = ''
        
        if provincia == 'CIUDAD DE BUENOS AIRES' or provincia == 'CAPITAL FEDERAL':
            provincia = 'C.A.B.A.'

        if 'BLUE' in direccion:
            return 14275

        if ('BEEPURE' in direccion): #significa que es la direccion Beepure
            return 13808

		
        sentence=f"SELECT ENT.EntID as entidad_id\
                    FROM ENT\
                    JOIN ENT21 ON ENT21.EntID = ENT.EntID \
                    JOIN LCL ON ENT21.LEnLclID = LCL.LclID \
                    JOIN PNC ON LCL.PncID = PNC.PncId \
                   WHERE ENT.EntEntIDC='{entidad_externa}'\
                     AND LCL.LclCP = {cp} \
                     AND upper(ENT.ENTOBS) = UPPER('{self.limpiar_string(obs)}') \
                     AND UPPER(PNC.PncNom) = UPPER('{self.limpiar_string(provincia)}') \
                     AND UPPER(ENT21.LEnDir) = UPPER('{self.limpiar_string(direccion)}')"
                     
                   
        print(sentence)
        with self.conn.cursor(as_dict=True) as cursor:
            cursor.execute(sentence)
            row_data = cursor.fetchone()
            if row_data != None:
                
                return row_data['entidad_id'] 
            else:
                return None

    def truncate_string(self, s, length):
        s = self.limpiar_string(s)
        return s[:length]
    
    def limpiar_string(self,texto):
        if not texto or texto.strip() == "":
            return ""
        # Solo conserva letras, números, espacios, signos de puntuación básicos, y el símbolo "@"
        texto_limpio = re.sub(r'[^A-Za-z0-9\s.,;:!#&()-]', '', texto)
        # Además, eliminamos las comillas simples (') y dobles (")
        texto_limpio = texto_limpio.replace("'", "").replace('"', "")
        return texto_limpio
    
    def generate_insert_query(self, data):
        data = {key: (value if value is not None else '') for key, value in data.items()}
        table_name = "[VKM_Interfaz_Prod].[dbo].[IntEntidad]"
        columns = [
                    '"INEntId"',                    # 1
                    '"INEntIdRel"',                 # 2
                    '"INEntOper"',                  # 3
                    '"INEntNombre"',                # 4
                    '"INEntDep"',                   # 5
                    '"INEntDest"',                  # 6
                    '"INEntOrig"',                  # 7
                    '"INEntDir"',                   # 8
                    '"INEntPuerta"',                # 9
                    '"INEntLclId"',                 # 10
                    '"INEntLclNom"',                # 11
                    '"INEntPrvId"',                 # 12
                    '"INEntPrvNom"',                # 13
                    '"INEntPaId"',                  # 14
                    '"INEntPaNom"',                 # 15
                    '"INEntCP"',                    # 16
                    '"INEntLaCoord"',               # 17
                    '"INEntLoCoord"',               # 18
                    '"INEntZona"',                  # 19
                    '"INEntSZona"',                 # 20
                    '"INEntTDI"',                   # 21
                    '"INEntNTdi"',                  # 22
                    '"INEntDvPrv"',                 # 23
                    '"INEntDPPass"',                # 24
                    '"INEEst"',                     # 25
                    '"INEntUsuReg"',                # 26
                    '"INEntFecReg"',                # 27
                    '"INEntAgc"',                   # 28
                    '"INEntIVA"',                   # 29
                    '"INEBlq"',                     # 30
                    '"INEntWMSAct"',                # 31
                    '"INEntTran"',                  # 32
                    '"INEntPrioridad"',             # 33
                    '"INEntObs"',                   # 34
                    '"INEntLogE"'                   # 35
                ]

        
       

        
        
        # Join the columns and values to form the query
        columns_str = ", ".join(columns)
        


        query = f"""INSERT INTO {table_name} ({columns_str}) 
                VALUES (
                '{self.truncate_string(str(data['cliente_id']),11)}', 
                NULL, 
                0, 
                '{self.truncate_string(data['nombre'],35)}',
                'N',
                'N',
                'S',
                '{self.truncate_string(data['direccion'],100)}',
                NULL,
                NULL,

                '{self.truncate_string(data['localidad'],100)}',
                NULL,
                '{self.truncate_string(data['provincia'], 100)}',
                NULL,
                NULL,
                '{self.truncate_string(str(data['codigo_postal']),10)}',
                NULL,
                NULL,
                NULL,
                NULL,
                
                80,
                '{self.truncate_string(str(data['cliente_id']), 11)}',
                NULL,
                NULL,
                '1',
                'vaclog',
                
                '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}',
                NULL,
                '1',
                NULL,


                NULL,
                NULL,
                NULL,
                '{self.truncate_string(data['observacion'],1024)}',
                '13781'
                  
                  
                  
                  
                  
                  );"""
        
        print(query)
        with self.conn.cursor(as_dict=True) as cursor:
            cursor.execute(query)
            self.conn.commit()

            # Cerrar la conexión
            cursor.close()

    
