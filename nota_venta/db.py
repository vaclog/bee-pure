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
            
    def getENT(self, entidad_externa):
        sentence=f"SELECT ENT.EntID as entidad_id\
                    FROM ENT\
                   WHERE ENT.EntEntIDC='{entidad_externa}'"
        
        cursor = self.cursor
        cursor.execute(sentence)
        if cursor.rowcount > 0:
            for row_data in cursor:
                return row_data['entidad_id'] 
        else:
            return None