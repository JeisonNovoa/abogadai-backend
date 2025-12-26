"""
Script directo para aplicar migraciones a producción
Usa psycopg2 con retry logic para conectarse
"""

import psycopg2
import time
import sys

# URL de conexión a la base de datos de producción
DB_CONFIG = {
    'host': 'dpg-d4stu1chg0os73csqgqg-a.virginia-postgres.render.com',
    'port': 5432,
    'database': 'abogadai_db',
    'user': 'abogadai_db_user',
    'password': 'zz2U57KjeZbinZqNAwIr2SICUnU68Ezj',
    'connect_timeout': 30
}

def column_exists(cursor, table_name, column_name):
    """Verifica si una columna existe en una tabla"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        );
    """, (table_name, column_name))
    return cursor.fetchone()[0]

def try_connect(max_retries=5, wait_seconds=10):
    """Intenta conectarse a la BD con retries"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Intento de conexión {attempt} de {max_retries}...")
            conn = psycopg2.connect(**DB_CONFIG)
            print("✓ Conexión exitosa!")
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries:
                print(f"✗ Error de conexión: {str(e)}")
                print(f"  Reintentando en {wait_seconds} segundos...")
                time.sleep(wait_seconds)
            else:
                print(f"✗ No se pudo conectar después de {max_retries} intentos")
                raise
    return None

def apply_migrations():
    """Aplica las migraciones a la base de datos"""

    print("=" * 70)
    print("APLICANDO MIGRACIONES A BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 70)
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    print("")

    # Intentar conectar con retries
    try:
        conn = try_connect(max_retries=5, wait_seconds=10)
        if not conn:
            sys.exit(1)

        cursor = conn.cursor()

        print("")
        print("MIGRACIÓN 1: Actualizar campos de caso (17-dic-2025)")
        print("-" * 70)

        # 1.1. Agregar campo ciudad_de_los_hechos
        if not column_exists(cursor, 'casos', 'ciudad_de_los_hechos'):
            print("   → Agregando campo 'ciudad_de_los_hechos'...")
            cursor.execute("""
                ALTER TABLE casos
                ADD COLUMN ciudad_de_los_hechos VARCHAR(100)
            """)
            conn.commit()
            print("   ✓ Campo 'ciudad_de_los_hechos' agregado exitosamente")
        else:
            print("   ○ Campo 'ciudad_de_los_hechos' ya existe, saltando...")

        # 1.2. Eliminar campo representante_legal
        if column_exists(cursor, 'casos', 'representante_legal'):
            print("   → Eliminando campo 'representante_legal'...")
            cursor.execute("""
                ALTER TABLE casos
                DROP COLUMN representante_legal
            """)
            conn.commit()
            print("   ✓ Campo 'representante_legal' eliminado exitosamente")
        else:
            print("   ○ Campo 'representante_legal' no existe, saltando...")

        print("")
        print("MIGRACIÓN 2: Agregar campos de paywall (19-dic-2025)")
        print("-" * 70)

        # 2.1. Agregar campo documento_desbloqueado
        if not column_exists(cursor, 'casos', 'documento_desbloqueado'):
            print("   → Agregando campo 'documento_desbloqueado'...")
            cursor.execute("""
                ALTER TABLE casos
                ADD COLUMN documento_desbloqueado BOOLEAN DEFAULT FALSE NOT NULL
            """)
            conn.commit()
            print("   ✓ Campo 'documento_desbloqueado' agregado exitosamente")
        else:
            print("   ○ Campo 'documento_desbloqueado' ya existe, saltando...")

        # 2.2. Agregar campo fecha_pago
        if not column_exists(cursor, 'casos', 'fecha_pago'):
            print("   → Agregando campo 'fecha_pago'...")
            cursor.execute("""
                ALTER TABLE casos
                ADD COLUMN fecha_pago TIMESTAMP
            """)
            conn.commit()
            print("   ✓ Campo 'fecha_pago' agregado exitosamente")
        else:
            print("   ○ Campo 'fecha_pago' ya existe, saltando...")

        print("")
        print("VERIFICACIÓN FINAL")
        print("-" * 70)

        # Obtener columnas finales
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'casos'
            ORDER BY ordinal_position
        """)

        print("Columnas en la tabla 'casos':")
        for row in cursor.fetchall():
            col_name, data_type, nullable, default = row
            nullable_str = "NULL" if nullable == 'YES' else "NOT NULL"
            default_str = f"DEFAULT {default}" if default else ""
            print(f"   • {col_name}: {data_type} {nullable_str} {default_str}")

        cursor.close()
        conn.close()

        print("")
        print("=" * 70)
        print("✓ MIGRACIONES COMPLETADAS EXITOSAMENTE")
        print("=" * 70)
        print("")
        print("RESUMEN DE CAMBIOS APLICADOS:")
        print("  • Campo 'ciudad_de_los_hechos' agregado (VARCHAR 100)")
        print("  • Campo 'representante_legal' eliminado")
        print("  • Campo 'documento_desbloqueado' agregado (BOOLEAN DEFAULT FALSE)")
        print("  • Campo 'fecha_pago' agregado (TIMESTAMP)")
        print("")

    except psycopg2.OperationalError as e:
        print("")
        print("=" * 70)
        print("✗ ERROR DE CONEXIÓN")
        print("=" * 70)
        print(f"No se pudo conectar a la base de datos de producción.")
        print(f"Descripción: {str(e)}")
        print("")
        print("POSIBLES CAUSAS:")
        print("  1. La base de datos está detrás de un firewall")
        print("  2. Se requiere VPN o IP en whitelist")
        print("  3. El hostname o credenciales son incorrectos")
        print("")
        print("SOLUCIÓN ALTERNATIVA:")
        print("  1. Ve a https://dashboard.render.com/")
        print("  2. Selecciona tu base de datos PostgreSQL")
        print("  3. Haz clic en 'Shell'")
        print("  4. Ejecuta el contenido de 'MIGRATION_SQL_FOR_PRODUCTION.sql'")
        print("")
        sys.exit(1)

    except Exception as e:
        print("")
        print("=" * 70)
        print("✗ ERROR DURANTE LA MIGRACIÓN")
        print("=" * 70)
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Descripción: {str(e)}")
        print("")
        print("La migración ha sido revertida. No se aplicaron cambios.")
        sys.exit(1)

if __name__ == "__main__":
    print("")
    print("Este script intentará conectarse directamente a la base de datos de producción")
    print("y aplicar las migraciones necesarias.")
    print("")
    response = input("¿Continuar? (yes/no): ")

    if response.lower() in ['yes', 'y', 'si', 's']:
        apply_migrations()
    else:
        print("Operación cancelada.")
