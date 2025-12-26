"""
Endpoints de Administración - Reembolsos y Métricas
Solo accesible para usuarios administradores
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..models.user import User
from ..models import Caso, Pago, EstadoCaso
from .auth import get_current_user
from ..services import pago_service, nivel_service

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency para verificar que el usuario es administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren permisos de administrador."
        )
    return current_user


@router.get("/reembolsos/pendientes")
async def listar_reembolsos_pendientes(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    📋 Lista solicitudes de reembolso pendientes de revisión

    Solo admin - Muestra todos los casos con solicitud de reembolso pendiente
    ordenados por fecha de solicitud (más antiguos primero)
    """
    try:
        casos_pendientes = pago_service.obtener_solicitudes_reembolso_pendientes(db)

        resultado = []
        for caso in casos_pendientes:
            # Obtener usuario del caso
            usuario = db.query(User).filter(User.id == caso.user_id).first()

            # Obtener pago asociado
            pago = db.query(Pago).filter(Pago.caso_id == caso.id).first()

            resultado.append({
                "caso_id": caso.id,
                "usuario": {
                    "id": usuario.id,
                    "email": usuario.email,
                    "nombre": f"{usuario.nombre} {usuario.apellido}"
                },
                "pago": {
                    "id": pago.id if pago else None,
                    "monto": float(pago.monto) if pago else None,
                    "fecha_pago": pago.fecha_pago if pago else None
                },
                "solicitud_reembolso": {
                    "fecha_solicitud": caso.fecha_solicitud_reembolso,
                    "motivo": caso.motivo_rechazo,
                    "evidencia_url": caso.evidencia_rechazo_url
                },
                "caso": {
                    "tipo_documento": caso.tipo_documento.value,
                    "nombre_solicitante": caso.nombre_solicitante,
                    "entidad_accionada": caso.entidad_accionada
                }
            })

        return {
            "total_pendientes": len(resultado),
            "solicitudes": resultado
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo solicitudes: {str(e)}"
        )


@router.post("/reembolsos/{caso_id}/procesar")
async def procesar_solicitud_reembolso(
    caso_id: int,
    aprobar: bool,
    comentario: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Aprueba o rechaza solicitud de reembolso

    Solo admin - Procesa la decisión sobre un reembolso solicitado

    Parámetros:
    - aprobar: True para aprobar, False para rechazar
    - comentario: Justificación de la decisión (visible para el usuario)
    """
    try:
        resultado = pago_service.procesar_reembolso(caso_id, aprobar, comentario, db)

        if aprobar:
            # TODO: Aquí se integraría con la pasarela de pago para reembolsar dinero real
            pass

        return {
            "success": True,
            "decision": "aprobado" if aprobar else "rechazado",
            "admin": current_user.email,
            **resultado
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando reembolso: {str(e)}"
        )


@router.get("/metricas/niveles")
async def obtener_metricas_niveles(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    📊 Métricas de distribución de niveles de usuarios

    Solo admin - Muestra estadísticas de cuántos usuarios hay en cada nivel
    y otras métricas relevantes del sistema
    """
    try:
        # Contar usuarios por nivel
        usuarios = db.query(User).all()

        distribucion_niveles = {
            0: {"nombre": "FREE", "count": 0, "usuarios": []},
            1: {"nombre": "BRONCE", "count": 0, "usuarios": []},
            2: {"nombre": "PLATA", "count": 0, "usuarios": []},
            3: {"nombre": "ORO", "count": 0, "usuarios": []}
        }

        for usuario in usuarios:
            nivel = usuario.nivel_usuario
            distribucion_niveles[nivel]["count"] += 1
            distribucion_niveles[nivel]["usuarios"].append({
                "id": usuario.id,
                "email": usuario.email,
                "pagos_ultimo_mes": usuario.pagos_ultimo_mes
            })

        # Estadísticas de casos
        total_casos = db.query(Caso).count()
        casos_pagados = db.query(Caso).filter(Caso.estado == EstadoCaso.PAGADO).count()
        casos_generados_sin_pagar = db.query(Caso).filter(Caso.estado == EstadoCaso.GENERADO).count()

        # Estadísticas de pagos
        total_pagos = db.query(Pago).count()
        ingresos_totales = db.query(Pago).with_entities(db.func.sum(Pago.monto)).scalar() or 0

        return {
            "usuarios": {
                "total": len(usuarios),
                "distribucion_niveles": distribucion_niveles
            },
            "casos": {
                "total": total_casos,
                "pagados": casos_pagados,
                "generados_sin_pagar": casos_generados_sin_pagar,
                "tasa_conversion": round((casos_pagados / total_casos * 100), 2) if total_casos > 0 else 0
            },
            "pagos": {
                "total_transacciones": total_pagos,
                "ingresos_totales": float(ingresos_totales),
                "ticket_promedio": float(ingresos_totales / total_pagos) if total_pagos > 0 else 0
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo métricas: {str(e)}"
        )


@router.get("/metricas/reembolsos")
async def obtener_metricas_reembolsos(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    💸 Métricas de reembolsos

    Solo admin - Estadísticas sobre solicitudes de reembolso
    """
    try:
        # Casos con reembolso solicitado
        solicitudes_pendientes = db.query(Caso).filter(
            Caso.reembolso_solicitado == True,
            Caso.fecha_reembolso == None
        ).count()

        # Casos reembolsados
        casos_reembolsados = db.query(Caso).filter(
            Caso.estado == EstadoCaso.REEMBOLSADO
        ).count()

        # Total de reembolsos aprobados
        total_reembolsado = db.query(Pago).filter(
            Pago.fecha_reembolso != None
        ).with_entities(db.func.sum(Pago.monto)).scalar() or 0

        # Solicitudes rechazadas
        solicitudes_rechazadas = db.query(Caso).filter(
            Caso.reembolso_solicitado == False,
            Caso.fecha_reembolso != None,
            Caso.estado != EstadoCaso.REEMBOLSADO
        ).count()

        return {
            "solicitudes_pendientes": solicitudes_pendientes,
            "reembolsos_aprobados": casos_reembolsados,
            "reembolsos_rechazados": solicitudes_rechazadas,
            "total_reembolsado": float(total_reembolsado),
            "tasa_aprobacion": round((casos_reembolsados / (casos_reembolsados + solicitudes_rechazadas) * 100), 2) if (casos_reembolsados + solicitudes_rechazadas) > 0 else 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo métricas de reembolsos: {str(e)}"
        )


@router.get("/metricas")
async def obtener_metricas_completas(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    📊 Endpoint principal de métricas - Combina todas las métricas del dashboard

    Solo admin - Retorna todas las métricas necesarias para el dashboard en una sola llamada
    """
    try:
        # 1. USUARIOS Y NIVELES
        usuarios = db.query(User).all()
        total_usuarios = len(usuarios)

        # Contar por nivel
        niveles_count = {"FREE": 0, "BRONCE": 0, "PLATA": 0, "ORO": 0}
        nivel_map = {0: "FREE", 1: "BRONCE", 2: "PLATA", 3: "ORO"}

        for usuario in usuarios:
            nivel_nombre = nivel_map.get(usuario.nivel_usuario, "FREE")
            niveles_count[nivel_nombre] += 1

        # 2. REEMBOLSOS
        solicitudes_pendientes = db.query(Caso).filter(
            Caso.reembolso_solicitado == True,
            Caso.fecha_reembolso == None
        ).count()

        casos_reembolsados = db.query(Caso).filter(
            Caso.estado == EstadoCaso.REEMBOLSADO
        ).count()

        solicitudes_rechazadas = db.query(Caso).filter(
            Caso.reembolso_solicitado == False,
            Caso.fecha_reembolso != None,
            Caso.estado != EstadoCaso.REEMBOLSADO
        ).count()

        total_solicitudes = solicitudes_pendientes + casos_reembolsados + solicitudes_rechazadas

        # 3. DOCUMENTOS/CASOS
        total_casos = db.query(Caso).count()
        casos_pagados = db.query(Caso).filter(Caso.estado == EstadoCaso.PAGADO).count()

        # 4. SESIONES (placeholder - puedes implementar tracking real si existe)
        # Por ahora usamos valores simulados basados en casos
        sesiones_hoy = casos_pagados  # Aproximación
        promedio_por_usuario = round(total_casos / total_usuarios, 1) if total_usuarios > 0 else 0

        return {
            "usuarios": {
                "total": total_usuarios
            },
            "niveles": niveles_count,
            "reembolsos": {
                "pendientes": solicitudes_pendientes,
                "aprobados": casos_reembolsados,
                "rechazados": solicitudes_rechazadas,
                "total": total_solicitudes
            },
            "documentos": {
                "pagados": casos_pagados,
                "total": total_casos
            },
            "sesiones": {
                "hoy": sesiones_hoy,
                "promedio_por_usuario": promedio_por_usuario,
                "duracion_promedio": 15  # Placeholder en minutos
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo métricas: {str(e)}"
        )


@router.get("/reembolsos")
async def listar_reembolsos_con_filtro(
    estado: str = "pendientes",
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    📋 Lista solicitudes de reembolso con filtros

    Solo admin - Filtra solicitudes por estado ACTUAL:
    - pendientes: reembolso_solicitado=True (esperando decisión)
    - aprobadas: estado=REEMBOLSADO (aprobado y procesado)
    - rechazadas: reembolso_solicitado=False AND fecha_reembolso!=None (rechazado)
    - todas: Cualquier caso que haya tenido solicitud de reembolso alguna vez
    """
    try:
        # Base query: casos que tienen o tuvieron solicitud de reembolso
        query = db.query(Caso).filter(
            or_(
                Caso.reembolso_solicitado == True,
                Caso.fecha_reembolso != None,
                Caso.estado == EstadoCaso.REEMBOLSADO
            )
        )

        # Aplicar filtros según el estado ACTUAL
        if estado == "pendientes":
            # Solicitud activa esperando decisión del admin
            query = query.filter(Caso.reembolso_solicitado == True)
        elif estado == "aprobadas":
            # Reembolso aprobado y procesado
            query = query.filter(Caso.estado == EstadoCaso.REEMBOLSADO)
        elif estado == "rechazadas":
            # Última decisión fue rechazo
            query = query.filter(
                Caso.reembolso_solicitado == False,
                Caso.fecha_reembolso != None,
                Caso.estado != EstadoCaso.REEMBOLSADO
            )
        # Si es "todas", no aplicamos filtros adicionales

        casos = query.order_by(Caso.fecha_solicitud_reembolso.desc()).all()

        resultado = []
        for caso in casos:
            # Obtener usuario del caso
            usuario = db.query(User).filter(User.id == caso.user_id).first()

            # Obtener pago asociado
            pago = db.query(Pago).filter(Pago.caso_id == caso.id).first()

            # Determinar estado actual
            if caso.estado == EstadoCaso.REEMBOLSADO:
                estado_actual = "aprobado"
            elif caso.fecha_reembolso and not caso.reembolso_solicitado:
                estado_actual = "rechazado"
            else:
                estado_actual = "pendiente"

            resultado.append({
                "caso_id": caso.id,
                "usuario": {
                    "id": usuario.id if usuario else None,
                    "email": usuario.email if usuario else "Desconocido",
                    "nombre": f"{usuario.nombre} {usuario.apellido or ''}" if usuario else "Desconocido"
                },
                "monto": float(pago.monto) if pago else 0,
                "fecha_solicitud": caso.fecha_solicitud_reembolso.isoformat() if caso.fecha_solicitud_reembolso else None,
                "estado": estado_actual,
                "motivo": caso.motivo_rechazo or "No especificado",
                "evidencia_url": caso.evidencia_rechazo_url,
                "tipo_documento": caso.tipo_documento.value if caso.tipo_documento else "tutela"
            })

        return resultado

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo solicitudes de reembolso: {str(e)}"
        )


@router.post("/reembolsos/{caso_id}/aprobar")
async def aprobar_reembolso(
    caso_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    ✅ Aprobar solicitud de reembolso

    Solo admin - Aprueba una solicitud de reembolso pendiente
    """
    try:
        # Buscar el caso
        caso = db.query(Caso).filter(Caso.id == caso_id).first()
        if not caso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caso no encontrado"
            )

        # Verificar que tiene reembolso solicitado ACTIVO
        if not caso.reembolso_solicitado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este caso no tiene una solicitud de reembolso activa"
            )

        # Procesar el reembolso usando el servicio existente
        resultado = pago_service.procesar_reembolso(
            caso_id=caso_id,
            aprobar=True,
            comentario_admin="Aprobado por administrador",
            db=db
        )

        return {
            "success": True,
            "message": "Reembolso aprobado exitosamente",
            "caso_id": caso_id,
            **resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error aprobando reembolso: {str(e)}"
        )


@router.post("/reembolsos/{caso_id}/rechazar")
async def rechazar_reembolso(
    caso_id: int,
    body: dict,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    ❌ Rechazar solicitud de reembolso

    Solo admin - Rechaza una solicitud de reembolso con una razón
    Body: {"razon": "string"}
    """
    try:
        # Extraer razón del body
        razon = body.get("razon", "")

        # Validar que se proporcione una razón
        if not razon or not razon.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar una razón para el rechazo"
            )

        # Buscar el caso
        caso = db.query(Caso).filter(Caso.id == caso_id).first()
        if not caso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caso no encontrado"
            )

        # Verificar que tiene reembolso solicitado ACTIVO
        if not caso.reembolso_solicitado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este caso no tiene una solicitud de reembolso activa"
            )

        # Procesar el rechazo usando el servicio existente
        resultado = pago_service.procesar_reembolso(
            caso_id=caso_id,
            aprobar=False,
            comentario_admin=razon.strip(),
            db=db
        )

        return {
            "success": True,
            "message": "Reembolso rechazado",
            "caso_id": caso_id,
            "razon": razon.strip(),
            **resultado
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rechazando reembolso: {str(e)}"
        )
