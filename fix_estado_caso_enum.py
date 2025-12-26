"""
Script de migración para corregir valores de estado_caso en minúsculas a MAYÚSCULAS
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_estado_caso_enum():
    """Actualiza los valores de estado_caso de minúsculas a MAYÚSCULAS"""

    print(">> Iniciando migracion de estado_caso...")

    # Crear conexión a la base de datos
    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Primero ver todos los valores actuales del enum en la base de datos
            print("\n[INFO] Consultando valores del enum en la base de datos...")
            result = conn.execute(text("""
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'estadocaso'
                ORDER BY e.enumsortorder;
            """))

            enum_values = [row[0] for row in result.fetchall()]
            print(f"[INFO] Valores del enum 'estadocaso': {enum_values}")

            # Verificar si hay registros en la tabla
            result = conn.execute(text("SELECT COUNT(*) FROM casos"))
            total_casos = result.fetchone()[0]
            print(f"[INFO] Total de casos en la tabla: {total_casos}")

            if total_casos == 0:
                print("[OK] No hay registros en la tabla casos.")
                return

            # Ver distribución de estados actuales
            print("\n[INFO] Distribución de estados actuales:")
            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY count DESC
            """))

            rows = result.fetchall()
            for row in rows:
                print(f"   - {row[0]}: {row[1]} registros")

            print("\n[INFO] Diagnostico completo.")

    except Exception as e:
        print(f"\n[ERROR] Error durante la migracion: {e}")
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACION: Corregir valores de estado_caso")
    print("=" * 60)

    fix_estado_caso_enum()

    print("\n" + "=" * 60)
    print("Proceso finalizado!")
    print("=" * 60)
