import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()


class Config:
    
    def __init__(self) -> None:
        self.path = os.getenv('TO_PROCESS_PATH')
        self.master = os.getenv('PATH_MASTER')
        self.processed_path = os.getenv('PROCESSED_PATH')
        self.import_path = os.getenv('IMPORT_PATH')
        self.new_customer_path = os.getenv('NEW_CUSTOMER_PATH')
    
    def getPath(self):
        return self.path
        



