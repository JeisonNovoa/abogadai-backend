"""
Script para revertir el estado de pago de los casos de un usuario específico
"""
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def revertir_pagos_usuario(email: str):
    """Revierte el estado de pago de todos los casos de un usuario"""

    print(f">> Revirtiendo pagos del usuario: {email}\n")

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # 1. Encontrar el user_id del usuario
            print("[INFO] Buscando usuario...")
            result = conn.execute(text("""
                SELECT id, email, nombre
                FROM users
                WHERE email = :email
            """), {"email": email})

            user = result.fetchone()
            if not user:
                print(f"[ERROR] No se encontró el usuario con email: {email}")
                return

            user_id = user[0]
            print(f"[OK] Usuario encontrado:")
            print(f"   - ID: {user_id}")
            print(f"   - Email: {user[1]}")
            print(f"   - Nombre: {user[2]}")

            # 2. Ver los casos actuales del usuario
            print(f"\n[INFO] Casos actuales del usuario:")
            result = conn.execute(text("""
                SELECT id, estado, documento_desbloqueado, fecha_pago
                FROM casos
                WHERE user_id = :user_id
                ORDER BY id
            """), {"user_id": user_id})

            casos = result.fetchall()
            if not casos:
                print("   (sin casos)")
                return

            for caso in casos:
                print(f"   - Caso #{caso[0]}: estado={caso[1]}, desbloqueado={caso[2]}, fecha_pago={caso[3]}")

            # 3. Contar cuántos casos están en PAGADO
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM casos
                WHERE user_id = :user_id AND estado = 'PAGADO'
            """), {"user_id": user_id})

            casos_pagados = result.fetchone()[0]
            print(f"\n[INFO] Casos en estado PAGADO: {casos_pagados}")

            if casos_pagados == 0:
                print("[OK] No hay casos pagados para revertir")
                return

            # 4. Revertir los pagos
            print(f"\n[INFO] Revirtiendo {casos_pagados} casos a GENERADO...")
            result = conn.execute(text("""
                UPDATE casos
                SET
                    estado = 'GENERADO',
                    documento_desbloqueado = false,
                    fecha_pago = NULL
                WHERE user_id = :user_id AND estado = 'PAGADO'
            """), {"user_id": user_id})

            conn.commit()

            print(f"[OK] {result.rowcount} casos actualizados")

            # 5. Mostrar los casos después de la actualización
            print(f"\n[INFO] Casos después de la actualización:")
            result = conn.execute(text("""
                SELECT id, estado, documento_desbloqueado, fecha_pago
                FROM casos
                WHERE user_id = :user_id
                ORDER BY id
            """), {"user_id": user_id})

            casos = result.fetchall()
            for caso in casos:
                print(f"   - Caso #{caso[0]}: estado={caso[1]}, desbloqueado={caso[2]}, fecha_pago={caso[3]}")

            print(f"\n[OK] Proceso completado!")
            print(f"   Los documentos del usuario {email} ahora están en estado GENERADO")
            print(f"   y requieren pago para ser desbloqueados.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("REVERTIR PAGOS DE USUARIO")
    print("=" * 60)

    email_usuario = "jeison@teilur.com"
    revertir_pagos_usuario(email_usuario)

    print("\n" + "=" * 60)
    print("Proceso finalizado!")
    print("=" * 60)
