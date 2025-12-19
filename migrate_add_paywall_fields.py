"""
Migración: Agregar campos de sistema de paywall al modelo Caso

Este script agrega los siguientes campos al modelo Caso:
- documento_desbloqueado: Boolean (default=False, not null)
- fecha_pago: DateTime (nullable)

Estos campos implementan el sistema de bloqueo/desbloqueo de documentos generados.
Los usuarios deben "pagar" (simular pago en desarrollo) para desbloquear el documento completo
y habilitar la descarga en PDF.
"""

import sys
import os

# Agregar el directorio raíz al path para importar los módulos
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.core.database import engine
from app.models.caso import Caso  # Importar para asegurar que el modelo esté registrado

def migrate():
    """Ejecuta la migración para agregar campos de sistema de paywall"""

    print("Iniciando migración: Agregar campos de paywall...")

    with engine.connect() as conn:
        try:
            # 1. Agregar campo documento_desbloqueado
            print("   Agregando campo 'documento_desbloqueado'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN documento_desbloqueado BOOLEAN DEFAULT FALSE NOT NULL
            """))
            conn.commit()
            print("   OK: Campo 'documento_desbloqueado' agregado")

            # 2. Agregar campo fecha_pago
            print("   Agregando campo 'fecha_pago'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN fecha_pago TIMESTAMP
            """))
            conn.commit()
            print("   OK: Campo 'fecha_pago' agregado")

            print("EXITO: Migración completada exitosamente")
            print("Los campos del sistema de paywall han sido agregados al modelo Caso")
            print("")
            print("Notas importantes:")
            print("- Todos los documentos existentes iniciarán bloqueados (documento_desbloqueado=FALSE)")
            print("- Los usuarios deberán simular el pago para desbloquear cada documento")
            print("- La descarga de PDF estará bloqueada hasta el desbloqueo")
            print("- La descarga de DOCX permanece sin restricciones")

        except Exception as e:
            print(f"ERROR durante la migración: {str(e)}")
            print(f"   Tipo de error: {type(e).__name__}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
