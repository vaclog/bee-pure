import pymssql

import traceback
class DB:
    def __init__(self):
        self.server = '192.168.0.201'
        self.db = 'VKM_Prod'
        self.user = 'vaclog'
        self.password  = 'hola$$123'
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
            
    def getENT(self, entidad_externa, provincia, cp, direccion):
        
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
                   WHERE ENT.EntEntIDC='{entidad_externa}' \
                     AND LCL.LclCP = {cp} \
                     AND UPPER(PNC.PncNom) = UPPER('{provincia}') \
                     AND UPPER(ENT21.LEnDir) = UPPER('{direccion}')"
                     
                   
        print(sentence)
        with self.conn.cursor(as_dict=True) as cursor:
            cursor.execute(sentence)
            row_data = cursor.fetchone()
            if row_data != None:
                
                return row_data['entidad_id'] 
            else:
                return None