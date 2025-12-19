"""
Endpoint temporal para ejecutar migraciones en producción
Este endpoint se puede eliminar después de aplicar las migraciones
"""

from fastapi import APIRouter, HTTPException, Header
from sqlalchemy import text, inspect
from app.core.database import engine
from app.core.config import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migrations", tags=["migrations"])


def column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Verifica si una columna existe en una tabla"""
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


@router.post("/apply")
async def apply_migrations(
    x_migration_secret: str = Header(None, description="Clave secreta para autorizar migraciones")
) -> Dict[str, Any]:
    """
    Aplica las migraciones pendientes a la base de datos de producción.

    Requiere header: X-Migration-Secret con el valor correcto.

    Migraciones incluidas:
    - Agregar campo ciudad_de_los_hechos
    - Eliminar campo representante_legal
    - Agregar campo documento_desbloqueado
    - Agregar campo fecha_pago
    """

    # Validar clave secreta (usando la SECRET_KEY del .env)
    if not x_migration_secret or x_migration_secret != settings.SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Clave de migración inválida"
        )

    results = {
        "success": False,
        "migrations_applied": [],
        "migrations_skipped": [],
        "errors": [],
        "database_url": engine.url.database
    }

    try:
        inspector = inspect(engine)

        with engine.connect() as conn:
            logger.info("Iniciando aplicación de migraciones...")

            # =========================================================
            # MIGRACIÓN 1: Actualizar campos de caso (17-dic-2025)
            # =========================================================

            # 1.1. Agregar campo ciudad_de_los_hechos
            if not column_exists(inspector, 'casos', 'ciudad_de_los_hechos'):
                logger.info("Agregando campo 'ciudad_de_los_hechos'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN ciudad_de_los_hechos VARCHAR(100)
                """))
                conn.commit()
                results["migrations_applied"].append("ciudad_de_los_hechos agregado")
                logger.info("Campo 'ciudad_de_los_hechos' agregado exitosamente")
                # Refrescar inspector
                inspector = inspect(engine)
            else:
                results["migrations_skipped"].append("ciudad_de_los_hechos ya existe")
                logger.info("Campo 'ciudad_de_los_hechos' ya existe, saltando...")

            # 1.2. Eliminar campo representante_legal
            if column_exists(inspector, 'casos', 'representante_legal'):
                logger.info("Eliminando campo 'representante_legal'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    DROP COLUMN representante_legal
                """))
                conn.commit()
                results["migrations_applied"].append("representante_legal eliminado")
                logger.info("Campo 'representante_legal' eliminado exitosamente")
                # Refrescar inspector
                inspector = inspect(engine)
            else:
                results["migrations_skipped"].append("representante_legal no existe")
                logger.info("Campo 'representante_legal' no existe, saltando...")

            # =========================================================
            # MIGRACIÓN 2: Agregar campos de paywall (19-dic-2025)
            # =========================================================

            # 2.1. Agregar campo documento_desbloqueado
            if not column_exists(inspector, 'casos', 'documento_desbloqueado'):
                logger.info("Agregando campo 'documento_desbloqueado'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN documento_desbloqueado BOOLEAN DEFAULT FALSE NOT NULL
                """))
                conn.commit()
                results["migrations_applied"].append("documento_desbloqueado agregado")
                logger.info("Campo 'documento_desbloqueado' agregado exitosamente")
                # Refrescar inspector
                inspector = inspect(engine)
            else:
                results["migrations_skipped"].append("documento_desbloqueado ya existe")
                logger.info("Campo 'documento_desbloqueado' ya existe, saltando...")

            # 2.2. Agregar campo fecha_pago
            if not column_exists(inspector, 'casos', 'fecha_pago'):
                logger.info("Agregando campo 'fecha_pago'...")
                conn.execute(text("""
                    ALTER TABLE casos
                    ADD COLUMN fecha_pago TIMESTAMP
                """))
                conn.commit()
                results["migrations_applied"].append("fecha_pago agregado")
                logger.info("Campo 'fecha_pago' agregado exitosamente")
                # Refrescar inspector
                inspector = inspect(engine)
            else:
                results["migrations_skipped"].append("fecha_pago ya existe")
                logger.info("Campo 'fecha_pago' ya existe, saltando...")

            # Verificación final
            final_inspector = inspect(engine)
            final_columns = [col['name'] for col in final_inspector.get_columns('casos')]

            results["success"] = True
            results["final_columns"] = final_columns
            results["message"] = "Migraciones aplicadas exitosamente"

            logger.info("Migraciones completadas exitosamente")

            return results

    except Exception as e:
        logger.error(f"Error aplicando migraciones: {str(e)}", exc_info=True)
        results["errors"].append(str(e))
        results["message"] = f"Error aplicando migraciones: {str(e)}"
        raise HTTPException(
            status_code=500,
            detail=results
        )


@router.get("/status")
async def get_migration_status() -> Dict[str, Any]:
    """
    Verifica el estado de las migraciones sin aplicarlas.
    No requiere autenticación.
    """
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('casos')]

        required_columns = {
            'ciudad_de_los_hechos': 'ciudad_de_los_hechos' in columns,
            'documento_desbloqueado': 'documento_desbloqueado' in columns,
            'fecha_pago': 'fecha_pago' in columns
        }

        should_not_exist = {
            'representante_legal': 'representante_legal' in columns
        }

        all_migrations_applied = (
            all(required_columns.values()) and
            not any(should_not_exist.values())
        )

        return {
            "all_migrations_applied": all_migrations_applied,
            "required_columns": required_columns,
            "columns_that_should_not_exist": should_not_exist,
            "all_columns": columns
        }

    except Exception as e:
        logger.error(f"Error verificando estado de migraciones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando estado: {str(e)}"
        )
