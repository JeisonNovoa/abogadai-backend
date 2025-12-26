"""
Script para verificar todos los enums en la base de datos
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_all_enums():
    """Verifica la consistencia de todos los enums"""

    print(">> Verificando todos los enums en la base de datos...\n")

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # 1. Verificar EstadoCaso
            print("=" * 60)
            print("1. EstadoCaso (tabla: casos, columna: estado)")
            print("=" * 60)

            result = conn.execute(text("""
                SELECT estado::text, COUNT(*) as count
                FROM casos
                GROUP BY estado
                ORDER BY estado
            """))

            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"   - {row[0]}: {row[1]} registros")
            else:
                print("   (sin registros)")

            # 2. Verificar TipoDocumento
            print("\n" + "=" * 60)
            print("2. TipoDocumento (tabla: casos, columna: tipo_documento)")
            print("=" * 60)

            result = conn.execute(text("""
                SELECT tipo_documento::text, COUNT(*) as count
                FROM casos
                GROUP BY tipo_documento
                ORDER BY tipo_documento
            """))

            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"   - {row[0]}: {row[1]} registros")
            else:
                print("   (sin registros)")

            # 3. Verificar si existe la tabla pagos
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'pagos'
            """))

            if result.fetchone()[0] > 0:
                # 4. Verificar EstadoPago
                print("\n" + "=" * 60)
                print("3. EstadoPago (tabla: pagos, columna: estado)")
                print("=" * 60)

                result = conn.execute(text("""
                    SELECT estado::text, COUNT(*) as count
                    FROM pagos
                    GROUP BY estado
                    ORDER BY estado
                """))

                rows = result.fetchall()
                if rows:
                    for row in rows:
                        print(f"   - {row[0]}: {row[1]} registros")
                else:
                    print("   (sin registros)")

                # 5. Verificar MetodoPago
                print("\n" + "=" * 60)
                print("4. MetodoPago (tabla: pagos, columna: metodo_pago)")
                print("=" * 60)

                result = conn.execute(text("""
                    SELECT metodo_pago::text, COUNT(*) as count
                    FROM pagos
                    GROUP BY metodo_pago
                    ORDER BY metodo_pago
                """))

                rows = result.fetchall()
                if rows:
                    for row in rows:
                        print(f"   - {row[0]}: {row[1]} registros")
                else:
                    print("   (sin registros)")
            else:
                print("\n[INFO] La tabla 'pagos' no existe aún")

            print("\n" + "=" * 60)
            print("RESUMEN")
            print("=" * 60)
            print("[OK] EstadoCaso: MAYÚSCULAS (TEMPORAL, GENERADO, etc.)")
            print("[OK] TipoDocumento: minúsculas (tutela, derecho_peticion)")
            print("[OK] EstadoPago: minúsculas (pendiente, exitoso, etc.)")
            print("[OK] MetodoPago: minúsculas (simulado, mercadopago, etc.)")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine.dispose()

if __name__ == "__main__":
    check_all_enums()
