from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from livekit import api
from datetime import datetime, timedelta, date
import uuid

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User
from ..models.caso import Caso, TipoDocumento, EstadoCaso
from .auth import get_current_user
from ..services import sesion_service, nivel_service

router = APIRouter(prefix="/sesiones", tags=["Sesiones"])


@router.post("/iniciar")
async def iniciar_sesion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT MODIFICADO - Crea un caso pero NO genera token LiveKit

    Cambio según plan.md:
    - Solo crea el caso en estado BORRADOR
    - Pre-llena datos del perfil del usuario
    - Genera room_name único para uso futuro
    - NO genera token de LiveKit (eso se hace en /sesiones/{caso_id}/conectar)
    - NO marca fecha_inicio_sesion (eso se hace al conectar)

    NUEVO - Sistema de Límites:
    - Valida límites de sesión antes de crear caso
    - Retorna HTTP 429 si límite alcanzado
    """

    try:
        # 🔒 VALIDAR LÍMITES DE SESIÓN
        validacion = sesion_service.puede_crear_sesion(current_user.id, db)

        if not validacion["permitido"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Límite de sesiones alcanzado",
                    "razon": validacion["razon"],
                    "sesiones_disponibles": validacion["sesiones_disponibles"],
                    "minutos_disponibles": validacion["minutos_disponibles"]
                }
            )

        # 1. Crear nuevo caso (sin iniciar sesión de LiveKit aún)
        session_id = str(uuid.uuid4())

        # Crear el caso primero para obtener el ID
        nuevo_caso = Caso(
            user_id=current_user.id,
            tipo_documento=TipoDocumento.TUTELA,
            estado=EstadoCaso.BORRADOR,
            session_id=session_id,
            room_name=None,  # Se asignará después de obtener el ID
            # ❌ NO marcar fecha_inicio_sesion aquí (se marca al conectar)
            # fecha_inicio_sesion=datetime.utcnow(),
            # ✅ Auto-llenar TODOS los datos del perfil del usuario
            nombre_solicitante=f"{current_user.nombre} {current_user.apellido}",
            email_solicitante=current_user.email,
            identificacion_solicitante=current_user.identificacion if current_user.identificacion else None,
            direccion_solicitante=current_user.direccion if current_user.direccion else None,
            telefono_solicitante=current_user.telefono if current_user.telefono else None
        )

        db.add(nuevo_caso)
        db.commit()  # Commit para obtener el ID
        db.refresh(nuevo_caso)

        # Ahora que tenemos el ID, actualizar el room_name en formato esperado por el agente
        nuevo_caso.room_name = f"caso-{nuevo_caso.id}"  # ✅ Formato: caso-123
        db.commit()
        db.refresh(nuevo_caso)

        # 2. ✅ NO generar token de LiveKit aquí
        # El token se generará cuando el usuario presione "Iniciar sesión"
        # mediante el endpoint /sesiones/{caso_id}/conectar

        return {
            "caso_id": nuevo_caso.id,
            "session_id": session_id,
            "room_name": nuevo_caso.room_name,
            "tipo_documento": nuevo_caso.tipo_documento.value,
            "nombre_solicitante": nuevo_caso.nombre_solicitante
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creando caso: {str(e)}"
        )


@router.post("/{caso_id}/conectar")
async def conectar_sesion(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT NUEVO - Genera token de LiveKit para conectar a la sesión

    Cambio según plan.md:
    - Se llama cuando el usuario presiona "Iniciar sesión" en el estado Pre-llamada
    - Genera el token de acceso para LiveKit
    - Marca fecha_inicio_sesion
    - Retorna token y URL para que el frontend se conecte

    Este endpoint separa la creación del caso (POST /iniciar) de la conexión a LiveKit
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    try:
        # 1. Marcar inicio de sesión
        if not caso.fecha_inicio_sesion:
            caso.fecha_inicio_sesion = datetime.utcnow()
            caso.estado = EstadoCaso.TEMPORAL  # Cambiar a TEMPORAL (sesión activa)
            db.commit()

            # 📊 NO registrar en sesiones_diarias aquí - solo al finalizar/generar documento
            # Esto evita que sesiones abandonadas cuenten como sesión del día

        # 2. Generar token de LiveKit
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise HTTPException(
                status_code=500,
                detail="LiveKit credentials not configured"
            )

        token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        token.with_identity(f"user-{caso.id}")
        token.with_name(f"{current_user.nombre} {current_user.apellido}")
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=caso.room_name,
        ))
        token.with_metadata(f"caso_id:{caso.id}")  # Metadata importante para el agente
        token.with_ttl(timedelta(hours=2))

        access_token = token.to_jwt()

        return {
            "caso_id": caso.id,
            "room_name": caso.room_name,
            "livekit_url": settings.LIVEKIT_URL,
            "access_token": access_token,
            "user_identity": f"user-{caso.id}",
            "user_name": f"{current_user.nombre} {current_user.apellido}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando token de LiveKit: {str(e)}"
        )


@router.put("/{caso_id}/finalizar")
async def finalizar_sesion(
    caso_id: int,
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT CRÍTICO - Finaliza una sesión con el avatar

    Marca la fecha de finalización de la sesión
    NO cambia el estado porque el caso sigue en 'borrador' hasta que el usuario genere el documento

    NUEVO - Sistema de Límites:
    - Calcula duración real de la sesión
    - Registra minutos consumidos en sesiones_diarias
    """
    caso = db.query(Caso).filter(Caso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Verificar si ya fue finalizada anteriormente
    ya_fue_finalizada = caso.fecha_fin_sesion is not None

    caso.fecha_fin_sesion = datetime.utcnow()

    # Calcular duración en minutos
    duracion_minutos = 0
    if caso.fecha_inicio_sesion:
        duracion_segundos = (caso.fecha_fin_sesion - caso.fecha_inicio_sesion).total_seconds()
        duracion_minutos = int(duracion_segundos / 60)

        # 📊 Registrar fin de sesión con minutos consumidos
        # Solo se contará como sesión si es la primera vez que se finaliza y duró >1 min
        sesion_service.registrar_fin_sesion(caso.id, duracion_minutos, db, ya_fue_finalizada)

    db.commit()

    return {
        "message": "Sesión finalizada",
        "caso_id": caso_id,
        "duracion_minutos": duracion_minutos
    }


@router.get("/validar-limite")
async def validar_limite_sesion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔒 NUEVO - Valida si el usuario puede crear sesión sin crearla

    Retorna información de límites y disponibilidad
    El frontend puede usar esto para mostrar advertencias antes de iniciar
    """
    validacion = sesion_service.puede_crear_sesion(current_user.id, db)

    # Obtener uso actual del día
    hoy = date.today()
    uso = sesion_service.obtener_uso_diario(current_user.id, hoy, db)

    # Campos compatibles con el frontend (ModalConfirmarSesion)
    return {
        # Campos originales
        "puede_crear_sesion": validacion["permitido"],
        "permitido": validacion["permitido"],  # Alias
        "razon": validacion["razon"],
        # Campos que el modal espera
        "sesiones_usadas": uso["sesiones_creadas"],
        "sesiones_disponibles": validacion["sesiones_disponibles"],
        "minutos_usados": uso["minutos_consumidos"],
        "minutos_disponibles": validacion["minutos_disponibles"],
        "duracion_maxima_sesion": validacion["limite_minutos_sesion"],
        "limite_minutos_sesion": validacion["limite_minutos_sesion"]
    }


@router.get("/uso-diario")
async def obtener_uso_diario_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 NUEVO - Retorna uso de sesiones del día actual

    Útil para mostrar estadísticas al usuario
    """
    hoy = date.today()
    uso = sesion_service.obtener_uso_diario(current_user.id, hoy, db)
    limites = nivel_service.obtener_limites_usuario(current_user.id, db)

    # Calcular total de sesiones permitidas (base + extra)
    total_sesiones = uso["sesiones_base_permitidas"] + uso["sesiones_extra_bonus"]

    # Calcular minutos disponibles
    minutos_disponibles = limites["min_totales"]
    if minutos_disponibles is not None:
        minutos_disponibles = max(0, minutos_disponibles - uso["minutos_consumidos"])
    else:
        minutos_disponibles = 999999  # Sin límite (nivel ORO)

    # Formato compatible con frontend
    return {
        "fecha": uso["fecha"],
        # Frontend espera "sesiones_usadas" en lugar de "sesiones_creadas"
        "sesiones_usadas": uso["sesiones_creadas"],
        "sesiones_disponibles": total_sesiones,  # Total permitido (no disponibles restantes)
        # Frontend espera "minutos_usados" en lugar de "minutos_consumidos"
        "minutos_usados": uso["minutos_consumidos"],
        "minutos_disponibles": minutos_disponibles,
        # Mantener compatibilidad con versión anterior
        "sesiones_creadas": uso["sesiones_creadas"],
        "minutos_consumidos": uso["minutos_consumidos"],
        "sesiones_base_permitidas": uso["sesiones_base_permitidas"],
        "sesiones_extra_bonus": uso["sesiones_extra_bonus"]
    }
