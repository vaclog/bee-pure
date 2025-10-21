import os
from dotenv import load_dotenv


class Config:

    def __init__(self, env_path=None) -> None:
        # Si no se pasa una ruta, busca .env en el directorio de trabajo actual
        if env_path is None:
            env_path = os.path.join(os.getcwd(), '.env')

        # Cargar variables desde el archivo .env especificado
        load_dotenv(dotenv_path=env_path, override=True)
        self.path = os.getenv('TO_PROCESS_PATH')
        self.master = os.getenv('PATH_MASTER')
        self.processed_path = os.getenv('PROCESSED_PATH')
        self.import_path = os.getenv('IMPORT_PATH')
        self.new_customer_path = os.getenv('NEW_CUSTOMER_PATH')
        self.combos_path = os.getenv('COMBOS_PATH')
    def getPath(self):
        return self.path
        



