from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from livekit import api
from datetime import datetime, timedelta
import uuid
import logging

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User
from ..models.caso import Caso, TipoDocumento, EstadoCaso
from .auth import get_current_user

router = APIRouter(prefix="/livekit", tags=["livekit"])
logger = logging.getLogger(__name__)


@router.post("/token")
async def get_livekit_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔄 ENDPOINT LEGACY - Redirige a la nueva lógica de sesiones

    Genera un token de LiveKit Y crea un caso automáticamente
    Este endpoint mantiene compatibilidad con el frontend antiguo
    """
    logger.info(f"🔑 ========== POST /livekit/token INICIADO ==========")
    logger.info(f"   Usuario: {current_user.email} (ID: {current_user.id})")

    try:
        # 1. Crear nuevo caso (igual que /sesiones/iniciar)
        room_name = f"caso-{uuid.uuid4().hex[:12]}"
        session_id = str(uuid.uuid4())

        logger.info(f"📦 Creando nuevo caso...")
        logger.info(f"   Room name: {room_name}")
        logger.info(f"   Session ID: {session_id}")

        nuevo_caso = Caso(
            user_id=current_user.id,
            tipo_documento=TipoDocumento.TUTELA,
            estado=EstadoCaso.BORRADOR,
            session_id=session_id,
            room_name=room_name,
            fecha_inicio_sesion=datetime.utcnow(),
            nombre_solicitante=f"{current_user.nombre} {current_user.apellido}",
            email_solicitante=current_user.email
        )

        db.add(nuevo_caso)
        db.commit()
        db.refresh(nuevo_caso)

        logger.info(f"✅ Caso creado exitosamente - ID: {nuevo_caso.id}")

        # 2. Generar token de LiveKit
        logger.info(f"🎫 Generando token de LiveKit...")

        token = api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET
        )

        user_identity = f"user-{nuevo_caso.id}"
        user_name = f"{current_user.nombre} {current_user.apellido}"

        logger.info(f"   User identity: {user_identity}")
        logger.info(f"   User name: {user_name}")

        # Agregar permisos al token
        token.with_identity(user_identity).with_name(user_name).with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )

        # Agregar metadata con el caso_id (CRÍTICO para el agente)
        metadata = f"caso_id:{nuevo_caso.id}"
        token.with_metadata(metadata)

        logger.info(f"🔑 METADATA CRÍTICO AGREGADO AL TOKEN:")
        logger.info(f"   Metadata: '{metadata}'")
        logger.info(f"   caso_id incluido: {nuevo_caso.id}")

        # Tiempo de expiración del token (2 horas)
        token.with_ttl(timedelta(hours=2))

        # Generar el JWT
        jwt_token = token.to_jwt()

        logger.info(f"✅ Token generado exitosamente")
        logger.info(f"   JWT length: {len(jwt_token)} caracteres")

        response_data = {
            "token": jwt_token,
            "url": settings.LIVEKIT_URL,
            "room_name": room_name,
            "user_identity": user_identity,
            "user_name": user_name,
            "caso_id": nuevo_caso.id,  # NUEVO: retornar el caso_id
            "session_id": session_id
        }

        logger.info(f"📤 Response a enviar al frontend:")
        logger.info(f"   caso_id: {response_data['caso_id']}")
        logger.info(f"   room_name: {response_data['room_name']}")
        logger.info(f"   url: {response_data['url']}")
        logger.info(f"🔑 ========== POST /livekit/token FINALIZADO ==========\n")

        return response_data

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando token de LiveKit: {str(e)}"
        )
