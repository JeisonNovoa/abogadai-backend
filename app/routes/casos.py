from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import logging

from ..core.database import get_db
from ..models.user import User
from ..models.caso import Caso, EstadoCaso, TipoDocumento
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


@router.post("/{caso_id}/validar")
def validar_caso(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 VALIDACIÓN PRELIMINAR (NO BLOQUEANTE)

    Valida los campos del caso y retorna SOLO ADVERTENCIAS.
    Esta validación se usa después del auto-llenado con IA para que el usuario
    vea qué campos faltan o están mal formateados, pero NO bloquea el guardado.

    El frontend usa esto para mostrar advertencias visuales en tiempo real
    en el formulario.
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

    from ..core.validation_helper import validar_caso_preliminar

    tipo_doc = caso.tipo_documento.value if caso.tipo_documento else "tutela"
    resultado_validacion = validar_caso_preliminar(caso, tipo_doc)

    return {
        "caso_id": caso_id,
        "valido": resultado_validacion["valido"],
        "errores": resultado_validacion["errores"],  # Siempre vacío en validación preliminar
        "advertencias": resultado_validacion["advertencias"]
    }


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

        # 🔍 LOG: Datos extraídos completos (para debugging)
        logger.info(f"✅ Datos extraídos exitosamente - DUMP COMPLETO:")
        import json
        logger.info(json.dumps(datos_extraidos, indent=2, ensure_ascii=False))

        # 🔍 LOG: Resumen de datos extraídos
        logger.info(f"\n📊 RESUMEN DE EXTRACCIÓN:")
        logger.info(f"   Tipo documento: {datos_extraidos.get('tipo_documento', 'tutela').upper()}")
        logger.info(f"   Nombre solicitante: {'✅ ' + datos_extraidos.get('nombre_solicitante', '')[:30] if datos_extraidos.get('nombre_solicitante') else '❌ Vacío'}")
        logger.info(f"   Identificación: {'✅ ' + str(datos_extraidos.get('identificacion_solicitante', '')) if datos_extraidos.get('identificacion_solicitante') else '❌ Vacío'}")
        logger.info(f"   Dirección: {'✅ Extraído' if datos_extraidos.get('direccion_solicitante') else '❌ Vacío'}")
        logger.info(f"   Teléfono: {'✅ ' + str(datos_extraidos.get('telefono_solicitante', '')) if datos_extraidos.get('telefono_solicitante') else '❌ Vacío'}")
        logger.info(f"   Email: {'✅ ' + str(datos_extraidos.get('email_solicitante', '')) if datos_extraidos.get('email_solicitante') else '❌ Vacío'}")
        logger.info(f"   Hechos: {'✅ Extraído' if datos_extraidos.get('hechos') else '❌ Vacío'}")
        logger.info(f"   Derechos vulnerados: {'✅ Extraído' if datos_extraidos.get('derechos_vulnerados') else '❌ Vacío'}")
        logger.info(f"   Entidad accionada: {'✅ ' + str(datos_extraidos.get('entidad_accionada', '')) if datos_extraidos.get('entidad_accionada') else '❌ Vacío'}")
        logger.info(f"   Dirección entidad: {'✅ Extraído' if datos_extraidos.get('direccion_entidad') else '❌ Vacío'}")
        logger.info(f"   Pretensiones: {'✅ Extraído' if datos_extraidos.get('pretensiones') else '❌ Vacío'}")
        logger.info(f"   Fundamentos: {'✅ Extraído' if datos_extraidos.get('fundamentos_derecho') else '❌ Vacío'}")
        logger.info(f"   Pruebas: {'✅ Extraído' if datos_extraidos.get('pruebas') else '❌ Vacío'}")
        logger.info(f"   Actúa en representación: {datos_extraidos.get('actua_en_representacion', False)}")
        logger.info(f"   Hubo derecho petición previo: {datos_extraidos.get('hubo_derecho_peticion_previo', False)}")

        # 🎯 NUEVA LÓGICA: Actualizar el caso con TODOS los datos extraídos
        # Incluso si están vacíos, mal formateados o incompletos
        # Las validaciones mostrarán advertencias en el formulario, pero no bloquean el auto-llenado
        campos_actualizados = []

        # Actualizar tipo_documento (siempre, basado en la detección de IA)
        if datos_extraidos.get('tipo_documento'):
            tipo_doc = datos_extraidos['tipo_documento']
            if tipo_doc == 'tutela':
                caso.tipo_documento = TipoDocumento.TUTELA
            elif tipo_doc == 'derecho_peticion':
                caso.tipo_documento = TipoDocumento.DERECHO_PETICION
            campos_actualizados.append('tipo_documento')

        # Actualizar TODOS los campos, incluso si están vacíos o mal formateados
        # Esto permite que el usuario vea lo que la IA entendió y lo corrija si es necesario

        # Solo actualizar si el dato extraído no es None (pero sí si es string vacío)
        if 'hechos' in datos_extraidos:
            caso.hechos = datos_extraidos['hechos']
            campos_actualizados.append('hechos')

        if 'derechos_vulnerados' in datos_extraidos:
            caso.derechos_vulnerados = datos_extraidos['derechos_vulnerados']
            campos_actualizados.append('derechos_vulnerados')

        if 'entidad_accionada' in datos_extraidos:
            caso.entidad_accionada = datos_extraidos['entidad_accionada']
            campos_actualizados.append('entidad_accionada')

        if 'pretensiones' in datos_extraidos:
            caso.pretensiones = datos_extraidos['pretensiones']
            campos_actualizados.append('pretensiones')

        if 'fundamentos_derecho' in datos_extraidos:
            caso.fundamentos_derecho = datos_extraidos['fundamentos_derecho']
            campos_actualizados.append('fundamentos_derecho')

        # 🆕 DATOS DEL SOLICITANTE (actualizar siempre, tal cual la IA los captó)
        if 'nombre_solicitante' in datos_extraidos:
            caso.nombre_solicitante = datos_extraidos['nombre_solicitante']
            campos_actualizados.append('nombre_solicitante')

        if 'identificacion_solicitante' in datos_extraidos:
            # Guardar TAL CUAL la IA lo extrajo, incluso si está mal formateado
            # El usuario verá el warning en el formulario y podrá corregirlo
            caso.identificacion_solicitante = datos_extraidos['identificacion_solicitante']
            campos_actualizados.append('identificacion_solicitante')

        if 'direccion_solicitante' in datos_extraidos:
            caso.direccion_solicitante = datos_extraidos['direccion_solicitante']
            campos_actualizados.append('direccion_solicitante')

        if 'telefono_solicitante' in datos_extraidos:
            # Guardar TAL CUAL, el usuario verá el warning si está mal formateado
            caso.telefono_solicitante = datos_extraidos['telefono_solicitante']
            campos_actualizados.append('telefono_solicitante')

        if 'email_solicitante' in datos_extraidos:
            # Guardar TAL CUAL, el usuario verá el warning si está mal formateado
            caso.email_solicitante = datos_extraidos['email_solicitante']
            campos_actualizados.append('email_solicitante')

        # 🆕 DATOS DE LA ENTIDAD (campos adicionales)
        if 'direccion_entidad' in datos_extraidos:
            caso.direccion_entidad = datos_extraidos['direccion_entidad']
            campos_actualizados.append('direccion_entidad')

        if 'representante_legal' in datos_extraidos:
            caso.representante_legal = datos_extraidos['representante_legal']
            campos_actualizados.append('representante_legal')

        # 🆕 PRUEBAS
        if 'pruebas' in datos_extraidos:
            caso.pruebas = datos_extraidos['pruebas']
            campos_actualizados.append('pruebas')

        # 🆕 REPRESENTACIÓN (campos booleanos y de representación)
        if 'actua_en_representacion' in datos_extraidos:
            caso.actua_en_representacion = datos_extraidos['actua_en_representacion']
            campos_actualizados.append('actua_en_representacion')

        if 'nombre_representado' in datos_extraidos:
            caso.nombre_representado = datos_extraidos['nombre_representado']
            campos_actualizados.append('nombre_representado')

        if 'identificacion_representado' in datos_extraidos:
            caso.identificacion_representado = datos_extraidos['identificacion_representado']
            campos_actualizados.append('identificacion_representado')

        if 'relacion_representado' in datos_extraidos:
            caso.relacion_representado = datos_extraidos['relacion_representado']
            campos_actualizados.append('relacion_representado')

        if 'tipo_representado' in datos_extraidos:
            caso.tipo_representado = datos_extraidos['tipo_representado']
            campos_actualizados.append('tipo_representado')

        logger.info(f"💾 Guardando cambios en la base de datos...")
        logger.info(f"   Campos actualizados ({len(campos_actualizados)}): {', '.join(campos_actualizados) if campos_actualizados else 'Ninguno'}")

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

    # Validar datos mínimos según el tipo de documento
    if not caso.hechos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para analizar fortaleza se requiere al menos: hechos"
        )

    # Para tutelas, también se requieren derechos vulnerados
    if caso.tipo_documento.value == "tutela" and not caso.derechos_vulnerados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para analizar fortaleza de una tutela se requiere: hechos y derechos vulnerados"
        )

    try:
        datos_caso = {
            'hechos': caso.hechos,
            'derechos_vulnerados': caso.derechos_vulnerados,
            'pretensiones': caso.pretensiones or '',
            'entidad_accionada': caso.entidad_accionada or '',
            'fundamentos_derecho': caso.fundamentos_derecho or ''
        }

        # Pasar el tipo de documento al análisis de fortaleza
        tipo_doc = caso.tipo_documento.value if caso.tipo_documento else "tutela"
        resultado = ai_analysis_service.analizar_fortaleza_caso(datos_caso, tipo_documento=tipo_doc)

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

    VALIDACIÓN ESTRICTA: Este endpoint valida que todos los campos críticos
    estén completos y con formato válido antes de generar el documento.
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

    # 🔍 VALIDACIÓN ESTRICTA: Validar campos críticos según tipo de documento
    from ..core.validation_helper import validar_caso_completo

    tipo_doc = caso.tipo_documento.value if caso.tipo_documento else "tutela"
    resultado_validacion = validar_caso_completo(caso, tipo_doc)

    if not resultado_validacion["valido"]:
        # Retornar errores detallados para que el frontend los muestre
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "El caso tiene errores que deben corregirse antes de generar el documento",
                "errores": resultado_validacion["errores"],
                "advertencias": resultado_validacion["advertencias"]
            }
        )

    try:
        # Preparar datos para GPT
        datos_caso = {
            'nombre_solicitante': caso.nombre_solicitante,
            'identificacion_solicitante': caso.identificacion_solicitante,
            'direccion_solicitante': caso.direccion_solicitante,
            'telefono_solicitante': caso.telefono_solicitante,
            'email_solicitante': caso.email_solicitante,
            'actua_en_representacion': caso.actua_en_representacion,
            'nombre_representado': caso.nombre_representado,
            'identificacion_representado': caso.identificacion_representado,
            'relacion_representado': caso.relacion_representado,
            'tipo_representado': caso.tipo_representado,
            'entidad_accionada': caso.entidad_accionada,
            'direccion_entidad': caso.direccion_entidad,
            'representante_legal': caso.representante_legal,
            'hechos': caso.hechos,
            'derechos_vulnerados': caso.derechos_vulnerados,
            'pretensiones': caso.pretensiones,
            'fundamentos_derecho': caso.fundamentos_derecho,
            'pruebas': caso.pruebas,
        }

        # Generar documento según el tipo
        if caso.tipo_documento.value == 'tutela':
            documento_generado = openai_service.generar_tutela(datos_caso)
        else:
            documento_generado = openai_service.generar_derecho_peticion(datos_caso)

        # Actualizar caso con documento generado
        caso.documento_generado = documento_generado
        caso.estado = EstadoCaso.GENERADO

        # Realizar análisis completo del documento generado (pasando el tipo de documento)
        tipo_doc = caso.tipo_documento.value if caso.tipo_documento else "tutela"
        analisis_completo = ai_analysis_service.analisis_completo_documento(
            documento_generado,
            datos_caso,
            tipo_documento=tipo_doc
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

        # Nombre del archivo según el tipo de documento
        tipo_doc_nombre = "tutela" if caso.tipo_documento.value == "tutela" else "derecho_peticion"
        filename = f"{tipo_doc_nombre}_{caso.nombre_solicitante or 'documento'}_{caso.id}.pdf"

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

        # Nombre del archivo según el tipo de documento
        tipo_doc_nombre = "tutela" if caso.tipo_documento.value == "tutela" else "derecho_peticion"
        filename = f"{tipo_doc_nombre}_{caso.nombre_solicitante or 'documento'}_{caso.id}.docx"

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
