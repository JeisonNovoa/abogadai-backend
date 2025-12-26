"""
Servicio para validación de límites de sesiones
"""

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import User, SesionDiaria, Caso
from .nivel_service import obtener_limites_usuario


def puede_crear_sesion(user_id: int, db: Session) -> dict:
    """
    Valida si el usuario puede crear una nueva sesión hoy

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        dict: {
            "permitido": bool,
            "razon": str,
            "sesiones_disponibles": int,
            "minutos_disponibles": int,
            "limite_minutos_sesion": int
        }
    """
    usuario = db.query(User).filter(User.id == user_id).first()

    if not usuario:
        return {
            "permitido": False,
            "razon": "Usuario no encontrado",
            "sesiones_disponibles": 0,
            "minutos_disponibles": 0,
            "limite_minutos_sesion": 0
        }

    # Obtener límites del usuario según su nivel
    limites = obtener_limites_usuario(user_id, db)

    # Obtener o crear registro de uso diario
    hoy = date.today()
    sesion_diaria = db.query(SesionDiaria).filter(
        SesionDiaria.user_id == user_id,
        SesionDiaria.fecha == hoy
    ).first()

    if not sesion_diaria:
        # Primera sesión del día - permitir
        return {
            "permitido": True,
            "razon": "Primera sesión del día",
            "sesiones_disponibles": limites["sesiones_dia"] + usuario.sesiones_extra_hoy,
            "minutos_disponibles": limites["min_totales"] if limites["min_totales"] else 999999,
            "limite_minutos_sesion": limites["min_sesion"]
        }

    # Calcular sesiones disponibles (base + extra - usadas)
    total_permitidas = limites["sesiones_dia"] + usuario.sesiones_extra_hoy
    sesiones_disponibles = total_permitidas - sesion_diaria.sesiones_creadas

    # Validar límite de sesiones por día
    if sesiones_disponibles <= 0:
        return {
            "permitido": False,
            "razon": f"Límite diario alcanzado ({total_permitidas} sesiones). Paga un documento para desbloquear +2 sesiones bonus.",
            "sesiones_disponibles": 0,
            "minutos_disponibles": 0,
            "limite_minutos_sesion": limites["min_sesion"]
        }

    # Validar límite de minutos totales del día (si aplica)
    minutos_disponibles = 999999  # Sin límite por defecto

    if limites["min_totales"] is not None:
        minutos_disponibles = limites["min_totales"] - sesion_diaria.minutos_consumidos

        if minutos_disponibles <= 0:
            return {
                "permitido": False,
                "razon": f"Límite de minutos diarios alcanzado ({limites['min_totales']} min). Vuelve mañana o paga para subir de nivel.",
                "sesiones_disponibles": sesiones_disponibles,
                "minutos_disponibles": 0,
                "limite_minutos_sesion": limites["min_sesion"]
            }

    # Todo OK - puede crear sesión
    return {
        "permitido": True,
        "razon": "OK",
        "sesiones_disponibles": sesiones_disponibles,
        "minutos_disponibles": minutos_disponibles,
        "limite_minutos_sesion": limites["min_sesion"]
    }


def registrar_inicio_sesion(user_id: int, caso_id: int, db: Session):
    """
    Registra que el usuario inició una sesión
    Actualiza contador en sesiones_diarias

    Args:
        user_id: ID del usuario
        caso_id: ID del caso/sesión iniciada
        db: Sesión de base de datos
    """
    hoy = date.today()
    limites = obtener_limites_usuario(user_id, db)
    usuario = db.query(User).filter(User.id == user_id).first()

    # Obtener o crear registro de uso diario
    sesion_diaria = db.query(SesionDiaria).filter(
        SesionDiaria.user_id == user_id,
        SesionDiaria.fecha == hoy
    ).first()

    if not sesion_diaria:
        # Crear nuevo registro
        sesion_diaria = SesionDiaria(
            user_id=user_id,
            fecha=hoy,
            sesiones_creadas=1,
            minutos_consumidos=0,
            sesiones_base_permitidas=limites["sesiones_dia"],
            sesiones_extra_bonus=usuario.sesiones_extra_hoy
        )
        db.add(sesion_diaria)
    else:
        # Incrementar contador
        sesion_diaria.sesiones_creadas += 1

    db.commit()

    return {
        "sesiones_creadas_hoy": sesion_diaria.sesiones_creadas,
        "minutos_consumidos_hoy": sesion_diaria.minutos_consumidos
    }


def registrar_fin_sesion(caso_id: int, duracion_minutos: int, db: Session, ya_fue_finalizada: bool = False):
    """
    Registra que la sesión terminó y actualiza minutos consumidos
    También registra la sesión como "creada" si aún no se registró (solo si duró >1 min)

    Args:
        caso_id: ID del caso/sesión finalizada
        duracion_minutos: Duración en minutos de la sesión
        db: Sesión de base de datos
        ya_fue_finalizada: True si es la primera vez que se finaliza esta sesión
    """
    caso = db.query(Caso).filter(Caso.id == caso_id).first()

    if not caso:
        raise ValueError(f"Caso {caso_id} no encontrado")

    hoy = date.today()
    limites = obtener_limites_usuario(caso.user_id, db)
    usuario = db.query(User).filter(User.id == caso.user_id).first()

    # Solo contar la sesión si:
    # 1. Es la primera vez que se finaliza (ya_fue_finalizada = False)
    # 2. Y duró más de 1 minuto
    debe_contar_sesion = not ya_fue_finalizada and duracion_minutos > 1

    # Buscar o crear registro de uso diario
    sesion_diaria = db.query(SesionDiaria).filter(
        SesionDiaria.user_id == caso.user_id,
        SesionDiaria.fecha == hoy
    ).first()

    if not sesion_diaria:
        # Crear nuevo registro solo si debe contar la sesión
        if debe_contar_sesion:
            sesion_diaria = SesionDiaria(
                user_id=caso.user_id,
                fecha=hoy,
                sesiones_creadas=1,
                minutos_consumidos=duracion_minutos,
                sesiones_base_permitidas=limites["sesiones_dia"],
                sesiones_extra_bonus=usuario.sesiones_extra_hoy
            )
            db.add(sesion_diaria)
    else:
        # Actualizar minutos consumidos
        sesion_diaria.minutos_consumidos += duracion_minutos

        # Incrementar contador de sesiones solo si debe contar
        if debe_contar_sesion:
            sesion_diaria.sesiones_creadas += 1

        sesion_diaria.updated_at = datetime.utcnow()

    db.commit()

    return {
        "minutos_consumidos_hoy": sesion_diaria.minutos_consumidos if sesion_diaria else 0,
        "duracion_sesion": duracion_minutos,
        "sesion_contada": debe_contar_sesion
    }


def obtener_uso_diario(user_id: int, fecha: date, db: Session) -> dict:
    """
    Obtiene el uso de sesiones del usuario para una fecha específica

    Args:
        user_id: ID del usuario
        fecha: Fecha a consultar
        db: Sesión de base de datos

    Returns:
        dict: {
            "fecha": str,
            "sesiones_creadas": int,
            "minutos_consumidos": int,
            "sesiones_base_permitidas": int,
            "sesiones_extra_bonus": int,
            "sesiones_disponibles": int
        }
    """
    sesion_diaria = db.query(SesionDiaria).filter(
        SesionDiaria.user_id == user_id,
        SesionDiaria.fecha == fecha
    ).first()

    usuario = db.query(User).filter(User.id == user_id).first()
    limites = obtener_limites_usuario(user_id, db)

    if not sesion_diaria:
        # No hay uso para esta fecha - retornar valores en cero
        return {
            "fecha": str(fecha),
            "sesiones_creadas": 0,
            "minutos_consumidos": 0,
            "sesiones_base_permitidas": limites["sesiones_dia"],
            "sesiones_extra_bonus": usuario.sesiones_extra_hoy if fecha == date.today() else 0,
            "sesiones_disponibles": limites["sesiones_dia"] + (usuario.sesiones_extra_hoy if fecha == date.today() else 0)
        }

    # Calcular sesiones disponibles
    total_permitidas = sesion_diaria.sesiones_base_permitidas + sesion_diaria.sesiones_extra_bonus
    sesiones_disponibles = max(0, total_permitidas - sesion_diaria.sesiones_creadas)

    return {
        "fecha": str(sesion_diaria.fecha),
        "sesiones_creadas": sesion_diaria.sesiones_creadas,
        "minutos_consumidos": sesion_diaria.minutos_consumidos,
        "sesiones_base_permitidas": sesion_diaria.sesiones_base_permitidas,
        "sesiones_extra_bonus": sesion_diaria.sesiones_extra_bonus,
        "sesiones_disponibles": sesiones_disponibles
    }


def desbloquear_sesiones_extra(user_id: int, cantidad: int, db: Session):
    """
    Desbloquea sesiones extra por pago (bonus inmediato)

    Args:
        user_id: ID del usuario
        cantidad: Cantidad de sesiones extra a desbloquear
        db: Sesión de base de datos
    """
    usuario = db.query(User).filter(User.id == user_id).first()

    if not usuario:
        raise ValueError(f"Usuario {user_id} no encontrado")

    # Incrementar sesiones extra de hoy
    usuario.sesiones_extra_hoy += cantidad

    # Actualizar también el registro de sesiones_diarias si existe
    hoy = date.today()
    sesion_diaria = db.query(SesionDiaria).filter(
        SesionDiaria.user_id == user_id,
        SesionDiaria.fecha == hoy
    ).first()

    if sesion_diaria:
        sesion_diaria.sesiones_extra_bonus = usuario.sesiones_extra_hoy

    db.commit()

    return {
        "sesiones_extra_hoy": usuario.sesiones_extra_hoy,
        "total_sesiones_disponibles": obtener_uso_diario(user_id, hoy, db)["sesiones_disponibles"]
    }
