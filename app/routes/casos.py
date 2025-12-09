from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import logging

from ..core.database import get_db
from ..models.user import User
from ..models.caso import Caso, EstadoCaso
from ..models.mensaje import Mensaje
from ..schemas.caso import CasoCreate, CasoUpdate, CasoResponse, CasoListResponse
from ..services import openai_service, document_service, ai_analysis_service
from .auth import get_current_user

router = APIRouter(prefix="/casos", tags=["Casos"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=CasoResponse, status_code=status.HTTP_201_CREATED)
def crear_caso(
    caso_data: CasoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo caso (tutela o derecho de petición) para el usuario autenticado
    """
    nuevo_caso = Caso(
        user_id=current_user.id,
        **caso_data.model_dump()
    )

    db.add(nuevo_caso)
    db.commit()
    db.refresh(nuevo_caso)

    return nuevo_caso


@router.get("/", response_model=List[CasoListResponse])
def listar_casos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos los casos del usuario autenticado
    """
    casos = db.query(Caso).filter(Caso.user_id == current_user.id).order_by(Caso.updated_at.desc()).all()
    return casos


@router.get("/{caso_id}", response_model=CasoResponse)
def obtener_caso(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles de un caso específico
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    return caso


@router.put("/{caso_id}", response_model=CasoResponse)
def actualizar_caso(
    caso_id: int,
    caso_data: CasoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza un caso existente (autoguardado de borradores)
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    # Actualizar solo los campos que se enviaron
    update_data = caso_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(caso, field, value)

    db.commit()
    db.refresh(caso)

    return caso


@router.delete("/{caso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_caso(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina un caso
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    db.delete(caso)
    db.commit()

    return None


@router.post("/{caso_id}/procesar-transcripcion", response_model=CasoResponse)
def procesar_transcripcion(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Procesa la transcripción de la conversación con IA y extrae datos estructurados
    para autollenar los campos del caso (hechos, derechos vulnerados, entidad, pretensiones).
    """
    # 🔍 LOG: Inicio del procesamiento
    logger.info(f"🤖 POST /casos/{caso_id}/procesar-transcripcion - Iniciando procesamiento")
    logger.info(f"   Usuario: {current_user.email}")

    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        logger.error(f"❌ Caso {caso_id} no encontrado o no pertenece al usuario {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    logger.info(f"✅ Caso {caso_id} encontrado - Estado: {caso.estado}")

    # 🔍 LOG: Consulta de mensajes
    logger.info(f"🔍 Buscando mensajes del caso {caso_id}...")

    # Obtener todos los mensajes del caso ordenados por timestamp
    mensajes = db.query(Mensaje).filter(
        Mensaje.caso_id == caso_id
    ).order_by(Mensaje.timestamp.asc()).all()

    # 🔍 LOG: Resultado de la consulta
    logger.info(f"📊 Mensajes encontrados: {len(mensajes)}")

    if not mensajes:
        logger.error(f"❌ No hay mensajes en el caso {caso_id}")
        logger.error(f"   Verificar: ¿Se guardaron los mensajes durante la sesión?")
        logger.error(f"   Revisar logs del agente de LiveKit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay mensajes en este caso para procesar"
        )

    # 🔍 LOG: Detalles de los mensajes
    logger.info(f"📝 Detalles de los mensajes:")
    for i, msg in enumerate(mensajes[:5], 1):  # Mostrar solo los primeros 5
        logger.info(f"   [{i}] {msg.remitente}: '{msg.texto[:50]}...' (ID: {msg.id})")
    if len(mensajes) > 5:
        logger.info(f"   ... y {len(mensajes) - 5} mensajes más")

    try:
        # Convertir mensajes a formato para el servicio de IA
        mensajes_formateados = [
            {
                "remitente": msg.remitente,
                "texto": msg.texto,
                "timestamp": str(msg.timestamp)
            }
            for msg in mensajes
        ]

        logger.info(f"🧠 Llamando a GPT-4o para extraer datos...")

        # Extraer datos con IA
        datos_extraidos = openai_service.extraer_datos_conversacion(mensajes_formateados)

        # 🔍 LOG: Datos extraídos
        logger.info(f"✅ Datos extraídos exitosamente:")
        logger.info(f"   Hechos: {'✅ Extraído' if datos_extraidos.get('hechos') else '❌ Vacío'}")
        logger.info(f"   Derechos vulnerados: {'✅ Extraído' if datos_extraidos.get('derechos_vulnerados') else '❌ Vacío'}")
        logger.info(f"   Entidad accionada: {'✅ Extraído' if datos_extraidos.get('entidad_accionada') else '❌ Vacío'}")
        logger.info(f"   Pretensiones: {'✅ Extraído' if datos_extraidos.get('pretensiones') else '❌ Vacío'}")
        logger.info(f"   Fundamentos: {'✅ Extraído' if datos_extraidos.get('fundamentos_derecho') else '❌ Vacío'}")

        # Actualizar el caso con los datos extraídos
        # Solo actualiza si el campo extraído no está vacío
        campos_actualizados = []

        if datos_extraidos.get('hechos'):
            caso.hechos = datos_extraidos['hechos']
            campos_actualizados.append('hechos')

        if datos_extraidos.get('derechos_vulnerados'):
            caso.derechos_vulnerados = datos_extraidos['derechos_vulnerados']
            campos_actualizados.append('derechos_vulnerados')

        if datos_extraidos.get('entidad_accionada'):
            caso.entidad_accionada = datos_extraidos['entidad_accionada']
            campos_actualizados.append('entidad_accionada')

        if datos_extraidos.get('pretensiones'):
            caso.pretensiones = datos_extraidos['pretensiones']
            campos_actualizados.append('pretensiones')

        if datos_extraidos.get('fundamentos_derecho'):
            caso.fundamentos_derecho = datos_extraidos['fundamentos_derecho']
            campos_actualizados.append('fundamentos_derecho')

        logger.info(f"💾 Guardando cambios en la base de datos...")
        logger.info(f"   Campos actualizados: {', '.join(campos_actualizados) if campos_actualizados else 'Ninguno'}")

        db.commit()
        db.refresh(caso)

        logger.info(f"✅ Caso {caso_id} actualizado exitosamente")

        return caso

    except Exception as e:
        logger.error(f"❌ Error procesando transcripción: {str(e)}")
        logger.error(f"   Tipo de error: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando transcripción: {str(e)}"
        )


@router.post("/{caso_id}/analizar-fortaleza", response_model=CasoResponse)
def analizar_fortaleza(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analiza la fortaleza del caso ANTES de generar el documento.
    Evalúa procedencia, derechos fundamentales, y probabilidad de éxito.
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    # Validar datos mínimos
    if not caso.hechos or not caso.derechos_vulnerados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para analizar fortaleza se requiere: hechos y derechos vulnerados"
        )

    try:
        datos_caso = {
            'hechos': caso.hechos,
            'derechos_vulnerados': caso.derechos_vulnerados,
            'pretensiones': caso.pretensiones or '',
            'entidad_accionada': caso.entidad_accionada or '',
            'fundamentos_derecho': caso.fundamentos_derecho or ''
        }

        resultado = ai_analysis_service.analizar_fortaleza_caso(datos_caso)

        if resultado.get('es_valido'):
            caso.analisis_fortaleza = resultado.get('fortaleza')
            db.commit()
            db.refresh(caso)

        return caso

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analizando fortaleza: {str(e)}"
        )


@router.post("/{caso_id}/generar", response_model=CasoResponse)
def generar_documento(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera el documento legal usando GPT-4 basado en los datos del caso.
    Incluye análisis automático de calidad y jurisprudencia.
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    # Validar que tenga los datos mínimos requeridos
    if not caso.nombre_solicitante or not caso.entidad_accionada or not caso.hechos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso debe tener al menos: nombre del solicitante, entidad accionada y hechos"
        )

    try:
        # Preparar datos para GPT
        datos_caso = {
            'nombre_solicitante': caso.nombre_solicitante,
            'identificacion_solicitante': caso.identificacion_solicitante,
            'direccion_solicitante': caso.direccion_solicitante,
            'telefono_solicitante': caso.telefono_solicitante,
            'email_solicitante': caso.email_solicitante,
            'entidad_accionada': caso.entidad_accionada,
            'direccion_entidad': caso.direccion_entidad,
            'representante_legal': caso.representante_legal,
            'hechos': caso.hechos,
            'derechos_vulnerados': caso.derechos_vulnerados,
            'pretensiones': caso.pretensiones,
            'fundamentos_derecho': caso.fundamentos_derecho,
        }

        # Generar documento según el tipo
        if caso.tipo_documento.value == 'tutela':
            documento_generado = openai_service.generar_tutela(datos_caso)
        else:
            documento_generado = openai_service.generar_derecho_peticion(datos_caso)

        # Actualizar caso con documento generado
        caso.documento_generado = documento_generado
        caso.estado = EstadoCaso.GENERADO

        # Realizar análisis completo del documento generado
        analisis_completo = ai_analysis_service.analisis_completo_documento(
            documento_generado,
            datos_caso
        )

        # Guardar análisis en el caso
        caso.analisis_jurisprudencia = analisis_completo.get('jurisprudencia')
        caso.analisis_calidad = analisis_completo.get('calidad')
        caso.sugerencias_mejora = analisis_completo.get('sugerencias')

        db.commit()
        db.refresh(caso)

        return caso

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando documento: {str(e)}"
        )


@router.get("/{caso_id}/descargar/pdf")
def descargar_pdf(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Descarga el documento generado como PDF
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    if not caso.documento_generado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso no tiene un documento generado"
        )

    try:
        # Generar PDF
        pdf_buffer = document_service.generar_pdf(
            caso.documento_generado,
            caso.nombre_solicitante or "documento"
        )

        # Nombre del archivo
        filename = f"tutela_{caso.nombre_solicitante or 'documento'}_{caso.id}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando PDF: {str(e)}"
        )


@router.get("/{caso_id}/descargar/docx")
def descargar_docx(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Descarga el documento generado como DOCX
    """
    caso = db.query(Caso).filter(
        Caso.id == caso_id,
        Caso.user_id == current_user.id
    ).first()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    if not caso.documento_generado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso no tiene un documento generado"
        )

    try:
        # Generar DOCX
        docx_buffer = document_service.generar_docx(
            caso.documento_generado,
            caso.nombre_solicitante or "documento"
        )

        # Nombre del archivo
        filename = f"tutela_{caso.nombre_solicitante or 'documento'}_{caso.id}.docx"

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando DOCX: {str(e)}"
        )
