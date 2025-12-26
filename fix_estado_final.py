"""
Script final para estandarizar estados a MAYÚSCULAS
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_estados_final():
    """Convierte TODOS los valores a MAYÚSCULAS"""

    print(">> Estandarizando estados a MAYUSCULAS...")

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Ver distribución actual
            print("\n[INFO] Estados actuales:")
            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY estado
            """))

            rows = result.fetchall()
            for row in rows:
                print(f"   - {row[0]}: {row[1]} registros")

            # Agregar valores en MAYÚSCULAS al enum si no existen
            print("\n[INFO] Asegurando valores en MAYUSCULAS en el enum...")
            valores_mayusculas = ['TEMPORAL', 'GENERADO', 'PAGADO', 'REEMBOLSADO', 'BORRADOR', 'FINALIZADO', 'ABANDONADO']

            for valor in valores_mayusculas:
                try:
                    conn.execute(text(f"ALTER TYPE estadocaso ADD VALUE IF NOT EXISTS '{valor}'"))
                    conn.commit()
                    print(f"   [OK] Valor '{valor}' agregado/verificado")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"   [SKIP] '{valor}' ya existe")
                    else:
                        print(f"   [SKIP] '{valor}': {e}")

            # Convertir todos los valores a MAYÚSCULAS
            print("\n[INFO] Convirtiendo todos los estados a MAYUSCULAS...")

            conversiones = [
                ("temporal", "TEMPORAL"),
                ("generado", "GENERADO"),
                ("pagado", "PAGADO"),
                ("reembolsado", "REEMBOLSADO"),
                ("borrador", "BORRADOR"),
                ("finalizado", "FINALIZADO"),
                ("abandonado", "ABANDONADO"),
            ]

            total_updated = 0
            for old_val, new_val in conversiones:
                try:
                    result = conn.execute(
                        text(f"UPDATE casos SET estado = '{new_val}' WHERE estado::text = '{old_val}'")
                    )
                    updated = result.rowcount
                    if updated > 0:
                        print(f"   [OK] {old_val} -> {new_val}: {updated} registros")
                        total_updated += updated
                except Exception as e:
                    print(f"   [ERROR] {old_val}: {e}")

            conn.commit()

            print(f"\n[OK] Conversion completada!")
            print(f"   Total actualizado: {total_updated}")

            # Ver distribución final
            print("\n[INFO] Estados finales:")
            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY estado
            """))

            rows = result.fetchall()
            for row in rows:
                print(f"   - {row[0]}: {row[1]} registros")

            # Verificar que NO hay valores en minúsculas
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM casos
                WHERE estado::text IN ('temporal', 'generado', 'pagado', 'reembolsado', 'borrador', 'finalizado', 'abandonado')
            """))

            minusculas_restantes = result.fetchone()[0]

            if minusculas_restantes == 0:
                print("\n[OK] Verificacion: No hay valores en minusculas")
            else:
                print(f"\n[WARN] Aun hay {minusculas_restantes} valores en minusculas")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("ESTANDARIZACION: Estados -> MAYUSCULAS")
    print("=" * 60)

    fix_estados_final()

    print("\n" + "=" * 60)
    print("Proceso finalizado!")
    print("=" * 60)
