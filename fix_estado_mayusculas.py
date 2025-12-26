"""
Script para convertir valores de estado en MAYÚSCULAS a minúsculas
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_estados_mayusculas():
    """Convierte valores de estado de MAYÚSCULAS a minúsculas"""

    print(">> Iniciando conversion de estados...")

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Ver distribución actual
            print("\n[INFO] Estados actuales:")
            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY count DESC
            """))

            rows = result.fetchall()
            for row in rows:
                print(f"   - {row[0]}: {row[1]} registros")

            # Convertir MAYÚSCULAS a minúsculas
            print("\n[INFO] Convirtiendo MAYÚSCULAS a minusculas...")

            conversiones = [
                ("GENERADO", "generado"),
                ("BORRADOR", "borrador"),
                ("FINALIZADO", "finalizado"),
                ("TEMPORAL", "temporal"),
                ("PAGADO", "pagado"),
                ("ABANDONADO", "abandonado"),
                ("REEMBOLSADO", "reembolsado"),
            ]

            total_updated = 0
            for old_val, new_val in conversiones:
                try:
                    # Primero agregamos el valor en minúsculas al enum si no existe
                    try:
                        conn.execute(text(f"ALTER TYPE estadocaso ADD VALUE IF NOT EXISTS '{new_val}'"))
                        conn.commit()
                    except:
                        pass  # Ya existe

                    # Luego actualizamos los registros
                    result = conn.execute(
                        text(f"UPDATE casos SET estado = '{new_val}' WHERE estado::text = '{old_val}'")
                    )
                    updated = result.rowcount
                    if updated > 0:
                        print(f"   [OK] {old_val} -> {new_val}: {updated} registros")
                        total_updated += updated
                except Exception as e:
                    print(f"   [SKIP] {old_val}: {e}")

            conn.commit()

            print(f"\n[OK] Conversion completada!")
            print(f"   Total actualizado: {total_updated}")

            # Ver distribución final
            print("\n[INFO] Estados finales:")
            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY count DESC
            """))

            rows = result.fetchall()
            for row in rows:
                print(f"   - {row[0]}: {row[1]} registros")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("CONVERSION: Estados MAYUSCULAS -> minusculas")
    print("=" * 60)

    fix_estados_mayusculas()

    print("\n" + "=" * 60)
    print("Proceso finalizado!")
    print("=" * 60)
