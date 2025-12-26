"""
Tareas programadas (CRON Jobs) para ejecución automática

Este módulo contiene las tareas que deben ejecutarse periódicamente:
- tarea_medianoche: Ejecutar a las 00:00 todos los días
- tarea_limpieza: Ejecutar a las 01:00 todos los días

Uso:
    python -m app.cron.tareas_diarias medianoche
    python -m app.cron.tareas_diarias limpieza
"""

import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def tarea_medianoche():
    """
    Ejecutar a las 00:00 todos los días

    Tareas:
    1. Recalcular niveles de todos los usuarios
    2. Resetear sesiones_extra_hoy a 0
    3. Limpiar sesiones_diarias antiguas (90+ días)
    """
    logger.info("=" * 60)
    logger.info("CRON: tarea_medianoche - INICIANDO")
    logger.info("=" * 60)

    from ..core.database import SessionLocal
    from ..services import nivel_service, limpieza_service

    db = SessionLocal()
    resultados = {
        "inicio": datetime.utcnow(),
        "exito": False,
        "errores": []
    }

    try:
        # 1. Recalcular niveles de todos los usuarios
        logger.info("\n1/3: Recalculando niveles de usuarios...")
        usuarios_actualizados = nivel_service.recalcular_todos_los_niveles(db)
        logger.info(f"   OK: {usuarios_actualizados} usuarios actualizados")
        resultados["usuarios_actualizados"] = usuarios_actualizados

        # 2. Resetear sesiones_extra_hoy
        logger.info("\n2/3: Reseteando sesiones extra...")
        sesiones_reseteadas = nivel_service.resetear_sesiones_extra(db)
        logger.info(f"   OK: {sesiones_reseteadas} usuarios con sesiones extra reseteadas")
        resultados["sesiones_reseteadas"] = sesiones_reseteadas

        # 3. Limpiar sesiones_diarias antiguas
        logger.info("\n3/3: Limpiando sesiones diarias antiguas (90+ días)...")
        sesiones_eliminadas = limpieza_service.limpiar_sesiones_diarias_antiguas(db, dias_antiguedad=90)
        logger.info(f"   OK: {sesiones_eliminadas} registros antiguos eliminados")
        resultados["sesiones_eliminadas"] = sesiones_eliminadas

        resultados["exito"] = True
        resultados["fin"] = datetime.utcnow()
        duracion = (resultados["fin"] - resultados["inicio"]).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("CRON: tarea_medianoche - COMPLETADA")
        logger.info(f"Duracion: {duracion:.2f} segundos")
        logger.info("=" * 60)

        return resultados

    except Exception as e:
        logger.error(f"\nERROR en tarea_medianoche: {str(e)}")
        import traceback
        traceback.print_exc()
        resultados["errores"].append(str(e))
        resultados["exito"] = False
        return resultados

    finally:
        db.close()


def tarea_limpieza():
    """
    Ejecutar a las 01:00 todos los días

    Tareas:
    1. Eliminar documentos GENERADOS vencidos (14+ días sin pagar)
    2. Eliminar casos TEMPORAL abandonados (1+ día sin completar)
    """
    logger.info("=" * 60)
    logger.info("CRON: tarea_limpieza - INICIANDO")
    logger.info("=" * 60)

    from ..core.database import SessionLocal
    from ..services import limpieza_service

    db = SessionLocal()
    resultados = {
        "inicio": datetime.utcnow(),
        "exito": False,
        "errores": []
    }

    try:
        # 1. Eliminar documentos vencidos
        logger.info("\n1/2: Eliminando documentos vencidos...")
        docs_eliminados = limpieza_service.eliminar_documentos_vencidos(db)
        logger.info(f"   OK: {docs_eliminados} documentos vencidos eliminados")
        resultados["documentos_eliminados"] = docs_eliminados

        # 2. Eliminar casos temporales antiguos
        logger.info("\n2/2: Eliminando casos temporales abandonados (1+ día)...")
        casos_eliminados = limpieza_service.eliminar_casos_temporales_antiguos(db, dias_antiguedad=1)
        logger.info(f"   OK: {casos_eliminados} casos temporales eliminados")
        resultados["casos_temporales_eliminados"] = casos_eliminados

        resultados["exito"] = True
        resultados["fin"] = datetime.utcnow()
        duracion = (resultados["fin"] - resultados["inicio"]).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("CRON: tarea_limpieza - COMPLETADA")
        logger.info(f"Duracion: {duracion:.2f} segundos")
        logger.info(f"Total eliminado: {docs_eliminados + casos_eliminados} registros")
        logger.info("=" * 60)

        return resultados

    except Exception as e:
        logger.error(f"\nERROR en tarea_limpieza: {str(e)}")
        import traceback
        traceback.print_exc()
        resultados["errores"].append(str(e))
        resultados["exito"] = False
        return resultados

    finally:
        db.close()


def tarea_completa():
    """
    Ejecuta todas las tareas en orden
    Útil para mantenimiento manual o testing
    """
    logger.info("\n" + "=" * 60)
    logger.info("EJECUTANDO TODAS LAS TAREAS DE MANTENIMIENTO")
    logger.info("=" * 60)

    resultados = {
        "medianoche": None,
        "limpieza": None,
        "inicio": datetime.utcnow()
    }

    try:
        # Ejecutar tarea_medianoche
        resultados["medianoche"] = tarea_medianoche()

        # Esperar un momento entre tareas
        logger.info("\n[Pausa entre tareas]\n")

        # Ejecutar tarea_limpieza
        resultados["limpieza"] = tarea_limpieza()

        resultados["fin"] = datetime.utcnow()
        duracion = (resultados["fin"] - resultados["inicio"]).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("TODAS LAS TAREAS COMPLETADAS")
        logger.info(f"Duracion total: {duracion:.2f} segundos")
        logger.info("=" * 60)

        return resultados

    except Exception as e:
        logger.error(f"\nERROR en tarea_completa: {str(e)}")
        import traceback
        traceback.print_exc()
        return resultados


# CLI Entry Point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUso: python -m app.cron.tareas_diarias [tarea]")
        print("\nTareas disponibles:")
        print("  medianoche  - Recalcular niveles, resetear sesiones extra, limpiar antiguas")
        print("  limpieza    - Eliminar documentos vencidos y casos temporales")
        print("  completa    - Ejecutar todas las tareas")
        print("\nEjemplos:")
        print("  python -m app.cron.tareas_diarias medianoche")
        print("  python -m app.cron.tareas_diarias limpieza")
        print("  python -m app.cron.tareas_diarias completa")
        sys.exit(1)

    tarea = sys.argv[1].lower()

    if tarea == "medianoche":
        resultado = tarea_medianoche()
    elif tarea == "limpieza":
        resultado = tarea_limpieza()
    elif tarea == "completa":
        resultado = tarea_completa()
    else:
        print(f"\nERROR: Tarea desconocida '{tarea}'")
        print("Tareas disponibles: medianoche, limpieza, completa")
        sys.exit(1)

    # Exit con código según éxito
    if isinstance(resultado, dict):
        # Verificar si es tarea_completa (tiene múltiples resultados)
        if "medianoche" in resultado or "limpieza" in resultado:
            # tarea_completa - verificar que ambas fueron exitosas
            exito_medianoche = resultado.get("medianoche", {}).get("exito", False)
            exito_limpieza = resultado.get("limpieza", {}).get("exito", False)
            sys.exit(0 if (exito_medianoche and exito_limpieza) else 1)
        else:
            # tarea individual
            sys.exit(0 if resultado.get("exito", False) else 1)
    else:
        sys.exit(0)
