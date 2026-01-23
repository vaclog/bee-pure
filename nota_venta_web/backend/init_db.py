"""
Script de inicialización de base de datos
Crea clientes, usuarios y configuraciones iniciales
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config.database import MySQLSessionLocal, init_db
from app.models import Cliente, Usuario, ConfiguracionCliente


def crear_cliente_microbel(db):
    """Crea cliente Microbel con su configuración"""
    print("📦 Creando cliente Microbel...")

    # Cliente
    cliente = Cliente(
        nombre="Microbel",
        codigo="microbel",
        email_notificacion="asagula@vaclog.com",
        activo=True
    )
    db.add(cliente)
    db.flush()  # Para obtener el ID

    # Usuario
    usuario = Usuario(
        username="microbel",
        email="microbel@vaclog.com",
        nombre_completo="Usuario Microbel",
        cliente_id=cliente.id,
        es_admin=False,
        puede_procesar=True,
        puede_validar=True,
        activo=True
    )
    usuario.set_password("microbel123")  # Cambiar en producción
    db.add(usuario)

    # Configuración
    config = ConfiguracionCliente(
        cliente_id=cliente.id,
        version=1,
        activa=True,
        mapeo_excel={
            "columnas": {
                "nombre": "A",
                "documento": "B",
                "provincia": "C",
                "cliente_id": "D",
                "direccion": "E",
                "fecha": "F",
                "numero_factura": "G",
                "sku": "H",
                "descripcion": "I",
                "cantidad": "J",
                "tipo": "K",
                "observacion": ["L", "M", "N", "O"],
                "codigo_postal": "P"
            },
            "header_row": 1,
            "data_start_row": 3,
            "validacion_header": "Razon Social"
        },
        master_file="C:/prg/bee-pure/microbel_nota_venta/masters/Combos.xlsx",
        rutas={
            "to_process": "C:/prg/bee-pure/microbel_nota_venta/to_process",
            "import_path": "C:/prg/bee-pure/microbel_nota_venta/import_to_valkimia",
            "processed_path": "C:/prg/bee-pure/microbel_nota_venta/processed",
            "new_customer_path": "C:/prg/bee-pure/microbel_nota_venta/new_customer",
            "combos_path": "C:/prg/bee-pure/microbel_nota_venta/combos"
        },
        notificaciones={
            "email_destino": "asagula@vaclog.com",
            "notificar_validacion": True,
            "notificar_procesamiento": True,
            "notificar_errores": True
        },
        descripcion="Configuración para Microbel - Mapeo de 16 columnas"
    )
    db.add(config)

    print("✓ Cliente Microbel creado")
    print(f"  Usuario: microbel / microbel123")


def crear_cliente_amande(db):
    """Crea cliente Amande con su configuración"""
    print("📦 Creando cliente Amande...")

    cliente = Cliente(
        nombre="Amande",
        codigo="amande",
        email_notificacion="asagula@vaclog.com",
        activo=True
    )
    db.add(cliente)
    db.flush()

    usuario = Usuario(
        username="amande",
        email="amande@vaclog.com",
        nombre_completo="Usuario Amande",
        cliente_id=cliente.id,
        activo=True
    )
    usuario.set_password("amande123")
    db.add(usuario)

    config = ConfiguracionCliente(
        cliente_id=cliente.id,
        version=1,
        activa=True,
        mapeo_excel={
            "columnas": {
                "nombre": "A",
                "documento": "B",
                "provincia": "C",
                "cliente_id": "D",
                "direccion": "E",
                "fecha": "F",
                "numero_factura": "G",
                "sku": "H",
                "descripcion": "I",
                "cantidad": "J",
                "tipo": "K",
                "observacion": ["L", "M", "N", "O"],
                "codigo_postal": "P",
                "fp": "Q"
            },
            "header_row": 1,
            "data_start_row": 3,
            "validacion_header": "Razon Social"
        },
        master_file="C:/prg/bee-pure/amande_nota_venta/masters/Combos.xlsx",
        rutas={
            "to_process": "C:/prg/bee-pure/amande_nota_venta/to_process",
            "import_path": "C:/prg/bee-pure/amande_nota_venta/import_to_valkimia",
            "processed_path": "C:/prg/bee-pure/amande_nota_venta/processed",
            "new_customer_path": "C:/prg/bee-pure/amande_nota_venta/new_customer",
            "combos_path": "C:/prg/bee-pure/amande_nota_venta/combos"
        },
        descripcion="Configuración para Amande - Mapeo de 17 columnas"
    )
    db.add(config)

    print("✓ Cliente Amande creado")
    print(f"  Usuario: amande / amande123")


def crear_usuario_admin(db):
    """Crea usuario administrador"""
    print("👤 Creando usuario administrador...")

    # Buscar primer cliente para asignar
    primer_cliente = db.query(Cliente).first()

    admin = Usuario(
        username="admin",
        email="admin@vaclog.com",
        nombre_completo="Administrador Sistema",
        cliente_id=primer_cliente.id if primer_cliente else 1,
        es_admin=True,
        puede_procesar=True,
        puede_validar=True,
        activo=True
    )
    admin.set_password("admin123")  # Cambiar en producción
    db.add(admin)

    print("✓ Usuario admin creado")
    print(f"  Usuario: admin / admin123")


def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 Inicializando base de datos Nota Venta Web")
    print("=" * 60)

    # Crear tablas
    print("\n📊 Creando tablas...")
    init_db()

    # Crear datos iniciales
    db = MySQLSessionLocal()

    try:
        # Verificar si ya existen datos
        if db.query(Cliente).count() > 0:
            print("\n⚠️  Ya existen datos en la base de datos")
            respuesta = input("¿Desea recrear los datos? (s/n): ")
            if respuesta.lower() != 's':
                print("❌ Operación cancelada")
                return

            # Limpiar datos
            print("\n🗑️  Limpiando datos existentes...")
            db.query(ConfiguracionCliente).delete()
            db.query(Usuario).delete()
            db.query(Cliente).delete()
            db.commit()

        # Crear clientes
        print("\n📦 Creando clientes...")
        crear_cliente_microbel(db)
        crear_cliente_amande(db)

        # Crear admin
        print("\n👤 Creando usuarios...")
        crear_usuario_admin(db)

        db.commit()

        print("\n" + "=" * 60)
        print("✅ Base de datos inicializada correctamente")
        print("=" * 60)
        print("\n📝 Usuarios creados:")
        print("  - admin / admin123 (administrador)")
        print("  - microbel / microbel123")
        print("  - amande / amande123")
        print("\n⚠️  IMPORTANTE: Cambiar contraseñas en producción\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
