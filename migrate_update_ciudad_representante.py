"""
Migración: Agregar ciudad_de_los_hechos y eliminar representante_legal

Este script realiza los siguientes cambios al modelo Caso:
- Agrega el campo ciudad_de_los_hechos: String(100) - para guardar la ciudad donde ocurrieron los hechos
- Elimina el campo representante_legal: ya no es necesario en el modelo

Fecha: 2025-12-17
"""

import sys
import os

# Agregar el directorio raíz al path para importar los módulos
sys.path.insert(0, os.path.dirname(__file__))

# Cargar variables de entorno antes de importar módulos de la app
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.core.database import engine
from app.models.caso import Caso  # Importar para asegurar que el modelo esté registrado

def migrate():
    """Ejecuta la migración para agregar ciudad_de_los_hechos y eliminar representante_legal"""

    print("Iniciando migración: Actualizar campos de caso...")

    with engine.connect() as conn:
        try:
            # 1. Agregar campo ciudad_de_los_hechos
            print("   Agregando campo 'ciudad_de_los_hechos'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN ciudad_de_los_hechos VARCHAR(100)
            """))
            conn.commit()
            print("   OK: Campo 'ciudad_de_los_hechos' agregado")

            # 2. Eliminar campo representante_legal
            print("   Eliminando campo 'representante_legal'...")
            conn.execute(text("""
                ALTER TABLE casos
                DROP COLUMN IF EXISTS representante_legal
            """))
            conn.commit()
            print("   OK: Campo 'representante_legal' eliminado")

            print("ÉXITO: Migración completada exitosamente")
            print("Los cambios han sido aplicados al modelo Caso")

        except Exception as e:
            print(f"ERROR durante la migración: {str(e)}")
            print(f"   Tipo de error: {type(e).__name__}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
