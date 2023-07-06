class Config:
    
    def __init__(self) -> None:
        self.path = r'C:\Python\src\deposito\bee-pure\nota_venta\to_process'
        self.master = r'C:\Python\src\deposito\bee-pure\nota_venta\masters\combos tienda.xlsx'
        self.processed_path = r'C:\Python\src\deposito\bee-pure\nota_venta\processed'
        self.import_path = r'C:\Python\src\deposito\bee-pure\nota_venta\import_to_valkimia'
        self.new_customer_path = r'C:\Python\src\deposito\bee-pure\nota_venta\new_customer'

    def getPath(self):
        return self.path
        