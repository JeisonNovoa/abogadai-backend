"""
Servicio para gestión de niveles de usuario
"""

from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import User, Pago, EstadoPago


def calcular_nivel_usuario(user_id: int, db: Session) -> int:
    """
    Calcula el nivel del usuario basado en pagos del último mes

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        int: 0=FREE, 1=BRONCE, 2=PLATA, 3=ORO
    """
    hace_30_dias = datetime.utcnow() - timedelta(days=30)

    # Contar pagos exitosos en últimos 30 días
    pagos_mes = db.query(Pago).filter(
        Pago.user_id == user_id,
        Pago.estado == EstadoPago.EXITOSO,
        Pago.fecha_pago >= hace_30_dias
    ).count()

    # Determinar nivel según cantidad de pagos
    if pagos_mes == 0:
        return 0  # FREE
    elif pagos_mes == 1:
        return 1  # BRONCE
    elif pagos_mes == 2:
        return 2  # PLATA
    else:  # 3 o más
        return 3  # ORO


def recalcular_todos_los_niveles(db: Session):
    """
    Recalcula niveles de todos los usuarios (CRON diario)

    Args:
        db: Sesión de base de datos
    """
    usuarios = db.query(User).all()

    for usuario in usuarios:
        nivel_nuevo = calcular_nivel_usuario(usuario.id, db)

        # Actualizar campos del usuario
        usuario.nivel_usuario = nivel_nuevo
        usuario.pagos_ultimo_mes = _contar_pagos_mes(usuario.id, db)
        usuario.ultimo_recalculo_nivel = datetime.utcnow()

    db.commit()

    return len(usuarios)


def obtener_limites_usuario(user_id: int, db: Session) -> dict:
    """
    Retorna los límites de sesión del usuario según su nivel

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        dict: {
            "nivel": int,
            "nombre_nivel": str,
            "sesiones_dia": int,
            "min_sesion": int,
            "min_totales": int or None
        }
    """
    usuario = db.query(User).filter(User.id == user_id).first()

    if not usuario:
        raise ValueError(f"Usuario {user_id} no encontrado")

    limites_por_nivel = {
        0: {  # FREE
            "sesiones_dia": 3,
            "min_sesion": 10,
            "min_totales": 30
        },
        1: {  # BRONCE
            "sesiones_dia": 5,
            "min_sesion": 10,
            "min_totales": 50
        },
        2: {  # PLATA
            "sesiones_dia": 7,
            "min_sesion": 10,
            "min_totales": 70
        },
        3: {  # ORO
            "sesiones_dia": 10,
            "min_sesion": 15,
            "min_totales": None  # Sin límite total
        }
    }

    nombres_nivel = {
        0: "FREE",
        1: "BRONCE",
        2: "PLATA",
        3: "ORO"
    }

    limites = limites_por_nivel.get(usuario.nivel_usuario, limites_por_nivel[0])

    return {
        "nivel": usuario.nivel_usuario,
        "nombre_nivel": nombres_nivel.get(usuario.nivel_usuario, "FREE"),
        **limites
    }


def actualizar_nivel_post_pago(user_id: int, db: Session):
    """
    Actualiza nivel inmediatamente después de un pago exitoso

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
    """
    usuario = db.query(User).filter(User.id == user_id).first()

    if not usuario:
        raise ValueError(f"Usuario {user_id} no encontrado")

    # Recalcular nivel
    nivel_nuevo = calcular_nivel_usuario(user_id, db)
    pagos_mes = _contar_pagos_mes(user_id, db)

    # Actualizar usuario
    usuario.nivel_usuario = nivel_nuevo
    usuario.pagos_ultimo_mes = pagos_mes
    usuario.ultimo_recalculo_nivel = datetime.utcnow()

    db.commit()

    return {
        "nivel_anterior": usuario.nivel_usuario,
        "nivel_nuevo": nivel_nuevo,
        "pagos_mes": pagos_mes
    }


def resetear_sesiones_extra(db: Session):
    """
    Resetea sesiones_extra_hoy a 0 para todos los usuarios (CRON medianoche)

    Args:
        db: Sesión de base de datos

    Returns:
        int: Cantidad de usuarios actualizados
    """
    usuarios_actualizados = db.query(User).filter(User.sesiones_extra_hoy > 0).all()

    for usuario in usuarios_actualizados:
        usuario.sesiones_extra_hoy = 0

    db.commit()

    return len(usuarios_actualizados)


def _contar_pagos_mes(user_id: int, db: Session) -> int:
    """
    Función auxiliar para contar pagos exitosos del último mes

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        int: Cantidad de pagos exitosos
    """
    hace_30_dias = datetime.utcnow() - timedelta(days=30)

    return db.query(Pago).filter(
        Pago.user_id == user_id,
        Pago.estado == EstadoPago.EXITOSO,
        Pago.fecha_pago >= hace_30_dias
    ).count()
