"""
Servicio para limpieza automática de datos (CRON jobs)
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models import Caso, SesionDiaria, EstadoCaso


def eliminar_documentos_vencidos(db: Session) -> int:
    """
    Elimina casos GENERADOS sin pagar que vencieron (14 días desde creación)

    Args:
        db: Sesión de base de datos

    Returns:
        int: Cantidad de casos eliminados
    """
    ahora = datetime.utcnow()

    # Buscar casos generados vencidos
    # NOTA: En PostgreSQL, el enum tiene 'GENERADO' en mayúsculas (legacy)
    from sqlalchemy import text
    casos_vencidos = db.query(Caso).filter(
        text("estado = 'GENERADO'"),
        Caso.documento_desbloqueado == False,
        Caso.fecha_vencimiento != None,
        Caso.fecha_vencimiento < ahora
    ).all()

    cantidad = len(casos_vencidos)

    # Eliminar casos
    for caso in casos_vencidos:
        db.delete(caso)

    db.commit()

    return cantidad


def eliminar_casos_temporales_antiguos(db: Session, dias_antiguedad: int = 1) -> int:
    """
    Elimina casos TEMPORAL abandonados (sin completar) después de N días

    Args:
        db: Sesión de base de datos
        dias_antiguedad: Días de antigüedad para considerar abandonado (default: 1)

    Returns:
        int: Cantidad de casos eliminados
    """
    limite = datetime.utcnow() - timedelta(days=dias_antiguedad)

    # Buscar casos temporales antiguos
    # NOTA: En PostgreSQL, el enum tiene 'temporal' en minúsculas (nuevo)
    from sqlalchemy import text
    casos_temporales = db.query(Caso).filter(
        text("estado = 'temporal'"),
        Caso.created_at < limite
    ).all()

    cantidad = len(casos_temporales)

    # Eliminar casos
    for caso in casos_temporales:
        db.delete(caso)

    db.commit()

    return cantidad


def limpiar_sesiones_diarias_antiguas(db: Session, dias_antiguedad: int = 90) -> int:
    """
    Elimina registros de sesiones_diarias mayores a N días

    Args:
        db: Sesión de base de datos
        dias_antiguedad: Días de antigüedad para eliminar (default: 90)

    Returns:
        int: Cantidad de registros eliminados
    """
    limite = datetime.utcnow() - timedelta(days=dias_antiguedad)

    # Buscar sesiones antiguas
    sesiones_antiguas = db.query(SesionDiaria).filter(
        SesionDiaria.fecha < limite.date()
    ).all()

    cantidad = len(sesiones_antiguas)

    # Eliminar sesiones
    for sesion in sesiones_antiguas:
        db.delete(sesion)

    db.commit()

    return cantidad


def ejecutar_limpieza_completa(db: Session) -> dict:
    """
    Ejecuta todas las tareas de limpieza y retorna resumen

    Args:
        db: Sesión de base de datos

    Returns:
        dict: Resumen de elementos eliminados por cada tarea
    """
    resultado = {
        "fecha_ejecucion": datetime.utcnow(),
        "documentos_vencidos_eliminados": 0,
        "casos_temporales_eliminados": 0,
        "sesiones_diarias_eliminadas": 0,
        "total_eliminados": 0
    }

    try:
        # 1. Eliminar documentos vencidos
        resultado["documentos_vencidos_eliminados"] = eliminar_documentos_vencidos(db)

        # 2. Eliminar casos temporales abandonados (1+ día)
        resultado["casos_temporales_eliminados"] = eliminar_casos_temporales_antiguos(db, dias_antiguedad=1)

        # 3. Limpiar sesiones diarias antiguas (90+ días)
        resultado["sesiones_diarias_eliminadas"] = limpiar_sesiones_diarias_antiguas(db, dias_antiguedad=90)

        # Calcular total
        resultado["total_eliminados"] = (
            resultado["documentos_vencidos_eliminados"] +
            resultado["casos_temporales_eliminados"] +
            resultado["sesiones_diarias_eliminadas"]
        )

        resultado["exito"] = True

    except Exception as e:
        resultado["exito"] = False
        resultado["error"] = str(e)

    return resultado


def obtener_estadisticas_limpieza(db: Session) -> dict:
    """
    Obtiene estadísticas de elementos candidatos para limpieza (sin eliminar)

    Args:
        db: Sesión de base de datos

    Returns:
        dict: Estadísticas de elementos que serían eliminados
    """
    ahora = datetime.utcnow()
    limite_temporal = ahora - timedelta(days=1)
    limite_sesiones = ahora - timedelta(days=90)

    # Contar casos vencidos
    documentos_vencidos = db.query(Caso).filter(
        Caso.estado == EstadoCaso.GENERADO,
        Caso.documento_desbloqueado == False,
        Caso.fecha_vencimiento != None,
        Caso.fecha_vencimiento < ahora
    ).count()

    # Contar casos temporales antiguos
    casos_temporales = db.query(Caso).filter(
        Caso.estado == EstadoCaso.TEMPORAL,
        Caso.created_at < limite_temporal
    ).count()

    # Contar sesiones antiguas
    sesiones_antiguas = db.query(SesionDiaria).filter(
        SesionDiaria.fecha < limite_sesiones.date()
    ).count()

    return {
        "documentos_vencidos_pendientes": documentos_vencidos,
        "casos_temporales_pendientes": casos_temporales,
        "sesiones_diarias_pendientes": sesiones_antiguas,
        "total_pendiente_limpieza": documentos_vencidos + casos_temporales + sesiones_antiguas
    }
