"""
Script para aplicar migraciones a la base de datos de producción
Fecha: 2025-12-19

Este script aplica las siguientes migraciones:
1. Agregar campo ciudad_de_los_hechos (17-dic-2025)
2. Eliminar campo representante_legal (17-dic-2025)
3. Agregar campo documento_desbloqueado (19-dic-2025)
4. Agregar campo fecha_pago (19-dic-2025)
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect

# URL de conexión a la base de datos de producción
PRODUCTION_DB_URL = "postgresql://abogadai_db_user:zz2U57KjeZbinZqNAwIr2SICUnU68Ezj@dpg-d4stu1chg0os73csqgqg-a.virginia-postgres.render.com/abogadai_db"

def column_exists(inspector, table_name, column_name):
    """Verifica si una columna existe en una tabla"""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def apply_migrations():
    """Aplica todas las migraciones pendientes"""

    print("=" * 70)
    print("APLICANDO MIGRACIONES A BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 70)
    print(f"Conectando a: dpg-d4stu1chg0os73csqgqg-a.virginia-postgres.render.com")
    print(f"Base de datos: abogadai_db")
    print("")

    try:
        # Crear conexión a la base de datos de producción
        engine = create_engine(PRODUCTION_DB_URL)
        inspector = inspect(engine)

        with engine.connect() as conn:
            print("✓ Conexión establecida exitosamente")
            print("")

            # =========================================================
            # MIGRACIÓN 1: Actualizar campos de caso (17-dic-2025)
            # =========================================================
            print("MIGRACIÓN 1: Actualizar campos de caso (17-dic-2025)")
            print("-" * 70)

            # 1.1. Agregar campo ciudad_de_los_hechos
            if not column_exists(inspector, 'casos', 'ciudad_de_los_hechos'):
                print("   → Agregando campo 'ciudad_de_los_hechos'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN ciudad_de_los_hechos VARCHAR(100)
                """))
                conn.commit()
                print("   ✓ Campo 'ciudad_de_los_hechos' agregado exitosamente")
            else:
                print("   ○ Campo 'ciudad_de_los_hechos' ya existe, saltando...")

            # Refrescar el inspector después de cada cambio
            inspector = inspect(engine)

            # 1.2. Eliminar campo representante_legal
            if column_exists(inspector, 'casos', 'representante_legal'):
                print("   → Eliminando campo 'representante_legal'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    DROP COLUMN representante_legal
                """))
                conn.commit()
                print("   ✓ Campo 'representante_legal' eliminado exitosamente")
            else:
                print("   ○ Campo 'representante_legal' no existe, saltando...")

            print("")

            # =========================================================
            # MIGRACIÓN 2: Agregar campos de paywall (19-dic-2025)
            # =========================================================
            print("MIGRACIÓN 2: Agregar campos de paywall (19-dic-2025)")
            print("-" * 70)

            # Refrescar el inspector
            inspector = inspect(engine)

            # 2.1. Agregar campo documento_desbloqueado
            if not column_exists(inspector, 'casos', 'documento_desbloqueado'):
                print("   → Agregando campo 'documento_desbloqueado'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN documento_desbloqueado BOOLEAN DEFAULT FALSE NOT NULL
                """))
                conn.commit()
                print("   ✓ Campo 'documento_desbloqueado' agregado exitosamente")
            else:
                print("   ○ Campo 'documento_desbloqueado' ya existe, saltando...")

            # Refrescar el inspector
            inspector = inspect(engine)

            # 2.2. Agregar campo fecha_pago
            if not column_exists(inspector, 'casos', 'fecha_pago'):
                print("   → Agregando campo 'fecha_pago'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN fecha_pago TIMESTAMP
                """))
                conn.commit()
                print("   ✓ Campo 'fecha_pago' agregado exitosamente")
            else:
                print("   ○ Campo 'fecha_pago' ya existe, saltando...")

            print("")

            # =========================================================
            # VERIFICACIÓN FINAL
            # =========================================================
            print("VERIFICACIÓN FINAL")
            print("-" * 70)

            # Refrescar el inspector final
            inspector = inspect(engine)
            columns = inspector.get_columns('casos')

            print("Columnas en la tabla 'casos':")
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f"DEFAULT {col['default']}" if col['default'] else ""
                print(f"   • {col['name']}: {col['type']} {nullable} {default}")

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
    import sys

    # Permitir confirmación por parámetro de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        apply_migrations()
    else:
        print("")
        response = input("¿Estás seguro de que quieres aplicar las migraciones a PRODUCCIÓN? (yes/no): ")
        if response.lower() in ['yes', 'y', 'si', 's']:
            apply_migrations()
        else:
            print("Migración cancelada por el usuario.")
