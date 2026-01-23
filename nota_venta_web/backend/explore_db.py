"""
Script para explorar la estructura de la base de datos deposito_prod
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pymysql
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('.env.example')

# Conectar a la base de datos
connection = pymysql.connect(
    host=os.getenv('REMITO_DB_HOST'),
    port=int(os.getenv('REMITO_DB_PORT')),
    user=os.getenv('REMITO_DB_USER'),
    password=os.getenv('REMITO_DB_PASSWORD'),
    database=os.getenv('REMITO_DB_DATABASE')
)

try:
    with connection.cursor() as cursor:
        print("=" * 80)
        print("📊 EXPLORANDO BASE DE DATOS: deposito_prod")
        print("=" * 80)

        # Listar todas las tablas
        print("\n📋 TABLAS EN LA BASE DE DATOS:\n")
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()

        for idx, tabla in enumerate(tablas, 1):
            print(f"  {idx}. {tabla[0]}")

        # Buscar tablas relacionadas con usuarios
        print("\n" + "=" * 80)
        print("🔍 BUSCANDO TABLAS DE USUARIOS/CUENTAS:\n")

        tablas_usuario = [t[0] for t in tablas if any(keyword in t[0].lower()
                          for keyword in ['user', 'usuario', 'cuenta', 'account', 'login', 'auth'])]

        if tablas_usuario:
            for tabla in tablas_usuario:
                print(f"\n📁 Tabla: {tabla}")
                print("-" * 80)

                # Mostrar estructura
                cursor.execute(f"DESCRIBE {tabla}")
                columnas = cursor.fetchall()

                print(f"{'Campo':<30} {'Tipo':<20} {'Null':<8} {'Key':<8} {'Default':<15}")
                print("-" * 80)
                for col in columnas:
                    campo, tipo, null, key, default = col[0], col[1], col[2], col[3], col[4]
                    default_str = str(default) if default else ''
                    print(f"{campo:<30} {str(tipo):<20} {null:<8} {key:<8} {default_str:<15}")

                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"\n📊 Total de registros: {count}")

                # Mostrar algunos registros de ejemplo
                if count > 0:
                    print(f"\n📄 Primeros 3 registros:")
                    cursor.execute(f"SELECT * FROM {tabla} LIMIT 3")
                    registros = cursor.fetchall()

                    # Obtener nombres de columnas
                    cursor.execute(f"DESCRIBE {tabla}")
                    nombres_columnas = [col[0] for col in cursor.fetchall()]

                    for reg in registros:
                        print("\n  ", "-" * 70)
                        for nombre, valor in zip(nombres_columnas, reg):
                            print(f"    {nombre}: {valor}")
        else:
            print("⚠️  No se encontraron tablas relacionadas con usuarios")

        # Buscar tablas de clientes/empresas
        print("\n" + "=" * 80)
        print("🏢 BUSCANDO TABLAS DE CLIENTES/EMPRESAS:\n")

        tablas_cliente = [t[0] for t in tablas if any(keyword in t[0].lower()
                          for keyword in ['cliente', 'client', 'empresa', 'company', 'customer'])]

        if tablas_cliente:
            for tabla in tablas_cliente:
                print(f"\n📁 Tabla: {tabla}")
                print("-" * 80)

                cursor.execute(f"DESCRIBE {tabla}")
                columnas = cursor.fetchall()

                print(f"{'Campo':<30} {'Tipo':<20} {'Null':<8} {'Key':<8}")
                print("-" * 80)
                for col in columnas:
                    print(f"{col[0]:<30} {str(col[1]):<20} {col[2]:<8} {col[3]:<8}")

                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"\n📊 Total de registros: {count}")
        else:
            print("⚠️  No se encontraron tablas de clientes")

        print("\n" + "=" * 80)
        print("✅ EXPLORACIÓN COMPLETADA")
        print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    connection.close()
