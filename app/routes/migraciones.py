"""
Endpoint temporal para ejecutar migraciones en producción
IMPORTANTE: Este archivo debe eliminarse después de ejecutar la migración
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from ..core.database import get_db, engine
from sqlalchemy.orm import Session
import logging

router = APIRouter(prefix="/migraciones", tags=["Migraciones"])
logger = logging.getLogger(__name__)

# ⚠️ IMPORTANTE: Cambiar esta clave por una segura y eliminar después de usar
SECRET_KEY_MIGRACION = "abogadai-migracion-subsidiariedad-2024-segura"

@router.post("/subsidiariedad")
async def ejecutar_migracion_subsidiariedad(
    secret_key: str,
    db: Session = Depends(get_db)
):
    """
    Ejecuta la migración para agregar campos de subsidiariedad

    IMPORTANTE:
    - Solo usar UNA VEZ en producción
    - Requiere secret_key correcto
    - Eliminar este endpoint después de usar
    """

    # Validar clave secreta
    if secret_key != SECRET_KEY_MIGRACION:
        logger.warning(f"❌ Intento de migración con clave incorrecta")
        raise HTTPException(status_code=403, detail="Clave secreta incorrecta")

    logger.info("🔄 Iniciando migración de subsidiariedad...")

    try:
        with engine.connect() as conn:
            # Verificar si ya existe alguno de los campos
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'casos'
                AND column_name = 'hubo_derecho_peticion_previo'
            """))

            if result.fetchone():
                logger.warning("⚠️ La migración ya fue ejecutada (campo ya existe)")
                return {
                    "status": "already_executed",
                    "message": "La migración ya fue ejecutada anteriormente"
                }

            # Ejecutar migraciones
            logger.info("📝 Agregando campo 'hubo_derecho_peticion_previo'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN hubo_derecho_peticion_previo BOOLEAN DEFAULT FALSE
            """))
            conn.commit()

            logger.info("📝 Agregando campo 'detalle_derecho_peticion_previo'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN detalle_derecho_peticion_previo TEXT
            """))
            conn.commit()

            logger.info("📝 Agregando campo 'tiene_perjuicio_irremediable'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN tiene_perjuicio_irremediable BOOLEAN DEFAULT FALSE
            """))
            conn.commit()

            logger.info("📝 Agregando campo 'es_procedente_tutela'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN es_procedente_tutela BOOLEAN DEFAULT FALSE
            """))
            conn.commit()

            logger.info("📝 Agregando campo 'razon_improcedencia'...")
            conn.execute(text("""
                ALTER TABLE casos
                ADD COLUMN razon_improcedencia TEXT
            """))
            conn.commit()

            logger.info("✅ Migración completada exitosamente")

            return {
                "status": "success",
                "message": "Migración de subsidiariedad ejecutada correctamente",
                "campos_agregados": [
                    "hubo_derecho_peticion_previo",
                    "detalle_derecho_peticion_previo",
                    "tiene_perjuicio_irremediable",
                    "es_procedente_tutela",
                    "razon_improcedencia"
                ]
            }

    except Exception as e:
        logger.error(f"❌ Error durante la migración: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando migración: {str(e)}"
        )


@router.get("/verificar")
async def verificar_campos_subsidiariedad():
    """
    Verifica si los campos de subsidiariedad ya existen en la BD
    No requiere autenticación, solo para verificar
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'casos'
                AND column_name IN (
                    'hubo_derecho_peticion_previo',
                    'detalle_derecho_peticion_previo',
                    'tiene_perjuicio_irremediable',
                    'es_procedente_tutela',
                    'razon_improcedencia'
                )
                ORDER BY column_name
            """))

            campos_existentes = [row[0] for row in result.fetchall()]

            campos_esperados = [
                'detalle_derecho_peticion_previo',
                'es_procedente_tutela',
                'hubo_derecho_peticion_previo',
                'razon_improcedencia',
                'tiene_perjuicio_irremediable'
            ]

            faltantes = [c for c in campos_esperados if c not in campos_existentes]

            return {
                "migracion_ejecutada": len(faltantes) == 0,
                "campos_existentes": campos_existentes,
                "campos_faltantes": faltantes,
                "total_campos": f"{len(campos_existentes)}/5"
            }

    except Exception as e:
        logger.error(f"❌ Error verificando campos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando campos: {str(e)}"
        )
