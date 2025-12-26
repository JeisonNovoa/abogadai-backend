"""
Migración: Agregar campo historial_reembolsos a la tabla casos

Este campo JSON almacenará el historial completo de solicitudes de reembolso
y decisiones del administrador, permitiendo múltiples solicitudes para el mismo caso.
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Agregar columna historial_reembolsos (JSON)
        try:
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN historial_reembolsos JSON DEFAULT NULL
            """))
            conn.commit()
            print("[OK] Columna 'historial_reembolsos' agregada exitosamente")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                print("[INFO] La columna 'historial_reembolsos' ya existe")
            else:
                print(f"[ERROR] Error agregando columna: {e}")
                raise

        print("\n[OK] Migracion completada exitosamente")

if __name__ == "__main__":
    migrate()
