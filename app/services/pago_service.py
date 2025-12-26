"""
Servicio para gestión de pagos y reembolsos
"""

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..models import Pago, Caso, User, EstadoPago, EstadoCaso, MetodoPago
from .nivel_service import actualizar_nivel_post_pago
from .sesion_service import desbloquear_sesiones_extra


def crear_pago_simulado(user_id: int, caso_id: int, monto: float, db: Session) -> Pago:
    """
    Crea un pago simulado (para desarrollo)

    Args:
        user_id: ID del usuario
        caso_id: ID del caso
        monto: Monto del pago
        db: Sesión de base de datos

    Returns:
        Pago: Objeto del pago creado
    """
    # Verificar que caso y usuario existen
    caso = db.query(Caso).filter(Caso.id == caso_id).first()
    usuario = db.query(User).filter(User.id == user_id).first()

    if not caso:
        raise ValueError(f"Caso {caso_id} no encontrado")

    if not usuario:
        raise ValueError(f"Usuario {user_id} no encontrado")

    if caso.user_id != user_id:
        raise ValueError(f"El caso {caso_id} no pertenece al usuario {user_id}")

    # Crear pago
    pago = Pago(
        user_id=user_id,
        caso_id=caso_id,
        monto=monto,
        estado=EstadoPago.EXITOSO,
        metodo_pago=MetodoPago.SIMULADO,
        referencia_pago=f"SIM-{datetime.utcnow().timestamp()}",
        fecha_pago=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(pago)
    db.commit()
    db.refresh(pago)

    # Procesar beneficios del pago
    procesar_pago_exitoso(pago.id, db)

    return pago


def procesar_pago_exitoso(pago_id: int, db: Session) -> dict:
    """
    Procesa un pago exitoso:
    1. Desbloquea documento
    2. Actualiza nivel del usuario
    3. Desbloquea sesiones extra

    Args:
        pago_id: ID del pago
        db: Sesión de base de datos

    Returns:
        dict: Información de beneficios desbloqueados
    """
    pago = db.query(Pago).filter(Pago.id == pago_id).first()

    if not pago:
        raise ValueError(f"Pago {pago_id} no encontrado")

    if pago.estado != EstadoPago.EXITOSO:
        raise ValueError(f"Pago {pago_id} no está en estado EXITOSO")

    caso = db.query(Caso).filter(Caso.id == pago.caso_id).first()

    if not caso:
        raise ValueError(f"Caso {pago.caso_id} no encontrado")

    # 1. Desbloquear documento
    caso.documento_desbloqueado = True
    caso.estado = EstadoCaso.PAGADO
    caso.fecha_pago = pago.fecha_pago

    # 2. Actualizar nivel del usuario
    nivel_info = actualizar_nivel_post_pago(pago.user_id, db)

    # 3. Desbloquear sesiones extra (+2 por cada pago)
    sesiones_info = desbloquear_sesiones_extra(pago.user_id, 2, db)

    db.commit()

    return {
        "documento_desbloqueado": True,
        "caso_id": caso.id,
        "nivel_actualizado": nivel_info,
        "sesiones_extra": sesiones_info,
        "beneficios": {
            "sesiones_bonus_hoy": 2,
            "nivel_nuevo": nivel_info["nivel_nuevo"],
            "pagos_mes": nivel_info["pagos_mes"]
        }
    }


def solicitar_reembolso(caso_id: int, motivo: str, evidencia_url: str, db: Session):
    """
    Registra solicitud de reembolso (permite múltiples solicitudes)

    Args:
        caso_id: ID del caso
        motivo: Motivo del rechazo legal
        evidencia_url: URL del documento de evidencia
        db: Sesión de base de datos
    """
    caso = db.query(Caso).filter(Caso.id == caso_id).first()

    if not caso:
        raise ValueError(f"Caso {caso_id} no encontrado")

    # Verificar que el caso está pagado (y no reembolsado)
    if caso.estado == EstadoCaso.REEMBOLSADO:
        raise ValueError("Este caso ya fue reembolsado")

    if caso.estado != EstadoCaso.PAGADO:
        raise ValueError("Solo se pueden solicitar reembolsos para casos pagados")

    # Verificar que existe un pago asociado
    pago = db.query(Pago).filter(
        Pago.caso_id == caso_id,
        Pago.estado == EstadoPago.EXITOSO
    ).first()

    if not pago:
        raise ValueError("No se encontró un pago exitoso para este caso")

    # Si ya tiene solicitud pendiente, no permitir duplicados
    if caso.reembolso_solicitado:
        raise ValueError("Ya existe una solicitud de reembolso pendiente para este caso")

    # Inicializar historial si no existe
    if caso.historial_reembolsos is None:
        caso.historial_reembolsos = []

    # Si hubo una decisión anterior (fecha_reembolso existe), resetear campos para nueva solicitud
    # El historial ya fue guardado en procesar_reembolso, no duplicar aquí
    if caso.fecha_reembolso is not None:
        # Resetear campos para la nueva solicitud
        caso.fecha_reembolso = None
        caso.comentario_admin_reembolso = None

    # Registrar nueva solicitud
    caso.reembolso_solicitado = True
    caso.fecha_solicitud_reembolso = datetime.utcnow()
    caso.motivo_rechazo = motivo
    caso.evidencia_rechazo_url = evidencia_url

    db.commit()

    return {
        "caso_id": caso.id,
        "reembolso_solicitado": True,
        "fecha_solicitud": caso.fecha_solicitud_reembolso,
        "motivo": motivo,
        "es_resolicitud": len(caso.historial_reembolsos) > 0
    }


def procesar_reembolso(caso_id: int, aprobar: bool, comentario_admin: str, db: Session):
    """
    Procesa aprobación/rechazo de reembolso (maneja historial)
    Si aprueba: reembolsa dinero, actualiza nivel
    Si rechaza: guarda en historial y permite re-solicitar

    Args:
        caso_id: ID del caso
        aprobar: True para aprobar, False para rechazar
        comentario_admin: Comentario del administrador
        db: Sesión de base de datos
    """
    caso = db.query(Caso).filter(Caso.id == caso_id).first()

    if not caso:
        raise ValueError(f"Caso {caso_id} no encontrado")

    # Verificar que existe solicitud de reembolso ACTIVA
    if not caso.reembolso_solicitado:
        raise ValueError("No existe solicitud de reembolso activa para este caso")

    # Buscar el pago asociado
    pago = db.query(Pago).filter(
        Pago.caso_id == caso_id,
        Pago.estado == EstadoPago.EXITOSO
    ).first()

    if not pago:
        raise ValueError("No se encontró un pago exitoso para este caso")

    # Inicializar historial si no existe
    if caso.historial_reembolsos is None:
        caso.historial_reembolsos = []

    # Registrar comentario del admin
    caso.comentario_admin_reembolso = comentario_admin

    if aprobar:
        # Aprobar reembolso
        pago.estado = EstadoPago.REEMBOLSADO
        pago.fecha_reembolso = datetime.utcnow()
        pago.motivo_reembolso = caso.motivo_rechazo

        caso.estado = EstadoCaso.REEMBOLSADO
        caso.fecha_reembolso = datetime.utcnow()
        caso.reembolso_solicitado = False  # Ya no está pendiente
        caso.documento_desbloqueado = False  # Bloquear documento nuevamente

        # Guardar en historial
        caso.historial_reembolsos.append({
            "tipo": "aprobacion",
            "fecha_solicitud": caso.fecha_solicitud_reembolso.isoformat() if caso.fecha_solicitud_reembolso else None,
            "motivo_usuario": caso.motivo_rechazo,
            "evidencia_url": caso.evidencia_rechazo_url,
            "fecha_decision": caso.fecha_reembolso.isoformat(),
            "comentario_admin": comentario_admin
        })
        flag_modified(caso, "historial_reembolsos")

        # Recalcular nivel del usuario (perdió un pago)
        nivel_info = actualizar_nivel_post_pago(caso.user_id, db)

        db.commit()

        return {
            "aprobado": True,
            "caso_id": caso.id,
            "pago_id": pago.id,
            "fecha_reembolso": pago.fecha_reembolso,
            "monto": float(pago.monto),
            "nivel_actualizado": nivel_info,
            "mensaje": "Reembolso procesado exitosamente"
        }
    else:
        # Rechazar solicitud de reembolso
        caso.reembolso_solicitado = False  # Ya no está pendiente (permite re-solicitar)
        caso.fecha_reembolso = datetime.utcnow()  # Registrar fecha de rechazo

        # Guardar en historial
        caso.historial_reembolsos.append({
            "tipo": "rechazo",
            "fecha_solicitud": caso.fecha_solicitud_reembolso.isoformat() if caso.fecha_solicitud_reembolso else None,
            "motivo_usuario": caso.motivo_rechazo,
            "evidencia_url": caso.evidencia_rechazo_url,
            "fecha_decision": caso.fecha_reembolso.isoformat(),
            "comentario_admin": comentario_admin
        })
        flag_modified(caso, "historial_reembolsos")

        db.commit()

        return {
            "aprobado": False,
            "caso_id": caso.id,
            "mensaje": "Solicitud de reembolso rechazada",
            "comentario_admin": comentario_admin,
            "puede_resolicitar": True
        }


def obtener_pagos_usuario(user_id: int, db: Session) -> List[Pago]:
    """
    Obtiene historial de pagos del usuario

    Args:
        user_id: ID del usuario
        db: Sesión de base de datos

    Returns:
        List[Pago]: Lista de pagos del usuario
    """
    pagos = db.query(Pago).filter(
        Pago.user_id == user_id
    ).order_by(Pago.created_at.desc()).all()

    return pagos


def obtener_solicitudes_reembolso_pendientes(db: Session) -> List[Caso]:
    """
    Obtiene todas las solicitudes de reembolso pendientes de revisión

    Args:
        db: Sesión de base de datos

    Returns:
        List[Caso]: Lista de casos con solicitud de reembolso pendiente
    """
    casos = db.query(Caso).filter(
        Caso.reembolso_solicitado == True,
        Caso.fecha_reembolso == None  # No procesados aún
    ).order_by(Caso.fecha_solicitud_reembolso.asc()).all()

    return casos


def verificar_puede_solicitar_reembolso(caso_id: int, db: Session) -> dict:
    """
    Verifica si un caso puede solicitar reembolso

    Args:
        caso_id: ID del caso
        db: Sesión de base de datos

    Returns:
        dict: {
            "puede_solicitar": bool,
            "razon": str
        }
    """
    caso = db.query(Caso).filter(Caso.id == caso_id).first()

    if not caso:
        return {
            "puede_solicitar": False,
            "razon": "Caso no encontrado"
        }

    if caso.estado != EstadoCaso.PAGADO:
        return {
            "puede_solicitar": False,
            "razon": "El caso debe estar pagado para solicitar reembolso"
        }

    if caso.reembolso_solicitado:
        return {
            "puede_solicitar": False,
            "razon": "Ya existe una solicitud de reembolso para este caso"
        }

    # Verificar que existe pago exitoso
    pago = db.query(Pago).filter(
        Pago.caso_id == caso_id,
        Pago.estado == EstadoPago.EXITOSO
    ).first()

    if not pago:
        return {
            "puede_solicitar": False,
            "razon": "No se encontró un pago exitoso para este caso"
        }

    return {
        "puede_solicitar": True,
        "razon": "OK"
    }
