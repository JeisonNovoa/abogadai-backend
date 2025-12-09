from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from ..core.database import get_db
from ..models.mensaje import Mensaje
from ..models.caso import Caso
from ..schemas.mensaje import MensajeCreate, MensajeResponse

router = APIRouter(prefix="/mensajes", tags=["Mensajes"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=MensajeResponse)
async def crear_mensaje(
    mensaje: MensajeCreate,
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT CRÍTICO - Webhook para guardar mensajes

    El agente llama este endpoint cada vez que hay:
    - Un mensaje del usuario (STT)
    - Una respuesta del asistente
    """
    # 🔍 LOG: Petición recibida
    logger.info(f"📨 POST /mensajes/ - Nueva petición recibida")
    logger.info(f"   Caso ID: {mensaje.caso_id}")
    logger.info(f"   Remitente: {mensaje.remitente}")
    logger.info(f"   Longitud texto: {len(mensaje.texto)} caracteres")
    logger.info(f"   Texto preview: '{mensaje.texto[:100]}...'")

    # Verificar que el caso existe
    caso = db.query(Caso).filter(Caso.id == mensaje.caso_id).first()
    if not caso:
        logger.error(f"❌ Caso {mensaje.caso_id} no encontrado en la base de datos")
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    logger.info(f"✅ Caso {mensaje.caso_id} encontrado - User ID: {caso.user_id}")

    try:
        nuevo_mensaje = Mensaje(**mensaje.model_dump())
        db.add(nuevo_mensaje)
        db.commit()
        db.refresh(nuevo_mensaje)

        logger.info(f"✅ Mensaje guardado exitosamente - ID: {nuevo_mensaje.id}")
        logger.info(f"   Timestamp: {nuevo_mensaje.timestamp}")

        # 🔍 LOG: Contar mensajes totales del caso
        total_mensajes = db.query(Mensaje).filter(Mensaje.caso_id == mensaje.caso_id).count()
        logger.info(f"📊 Total mensajes del caso {mensaje.caso_id}: {total_mensajes}")

        return nuevo_mensaje

    except Exception as e:
        logger.error(f"❌ Error al guardar mensaje en BD: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar mensaje: {str(e)}")


@router.get("/caso/{caso_id}", response_model=List[MensajeResponse])
async def obtener_mensajes_caso(
    caso_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los mensajes de un caso ordenados por timestamp
    """
    # Verificar que el caso existe
    caso = db.query(Caso).filter(Caso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    mensajes = db.query(Mensaje).filter(
        Mensaje.caso_id == caso_id
    ).order_by(Mensaje.timestamp).all()

    return mensajes
