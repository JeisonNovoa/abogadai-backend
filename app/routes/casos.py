from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from ..core.database import get_db
from ..models.user import User
from ..models.caso import Caso, EstadoCaso, TipoDocumento
from ..models.mensaje import Mensaje
from ..schemas.caso import CasoCreate, CasoUpdate, CasoResponse, CasoListResponse
from ..services import openai_service, document_service
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
    Auto-llena datos del solicitante desde el perfil del usuario
    """
    # Convertir a dict
    caso_dict = caso_data.model_dump()

    # Auto-llenar desde perfil si los campos están vacíos
    if not caso_dict.get('nombre_solicitante'):
        caso_dict['nombre_solicitante'] = f"{current_user.nombre} {current_user.apellido}"

    if not caso_dict.get('email_solicitante'):
        caso_dict['email_solicitante'] = current_user.email

    if not caso_dict.get('identificacion_solicitante') and current_user.identificacion:
        caso_dict['identificacion_solicitante'] = current_user.identificacion

    if not caso_dict.get('direccion_solicitante') and current_user.direccion:
        caso_dict['direccion_solicitante'] = current_user.direccion

    if not caso_dict.get('telefono_solicitante') and current_user.telefono:
        caso_dict['telefono_solicitante'] = current_user.telefono

    nuevo_caso = Caso(
        user_id=current_user.id,
        **caso_dict
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


@router.get("/prellenar-datos", response_model=dict)
def obtener_datos_prellenado(current_user: User = Depends(get_current_user)):
    """
    Retorna los datos del perfil del usuario para pre-llenar un caso nuevo
    El frontend puede usar esto antes de crear el caso
    """
    return {
        "nombre_solicitante": f"{current_user.nombre} {current_user.apellido}",
        "email_solicitante": current_user.email,
        "identificacion_solicitante": current_user.identificacion or "",
        "direccion_solicitante": current_user.direccion or "",
        "telefono_solicitante": current_user.telefono or "",
        "perfil_completo": current_user.perfil_completo
    }


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


@router.get("/{caso_id}/campos-criticos")
def obtener_campos_criticos(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎯 ENDPOINT NUEVO - Retorna campos críticos y sensibles según tipo de documento

    Según plan.md:
    - Campos bloqueantes: impiden generar documento si están vacíos
    - Campos sensibles: recomendados revisar, pero no bloquean generación
    - Datos del solicitante: siempre en solo lectura (vienen del perfil)

    El frontend usa esto para:
    1. Mostrar indicadores visuales de campos obligatorios
    2. Bloquear botón "Generar documento" si faltan campos críticos
    3. Mostrar confirmación de datos sensibles antes de generar
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

    tipo_doc = caso.tipo_documento.value if caso.tipo_documento else "tutela"

    # Campos bloqueantes según tipo de documento (plan.md líneas 77-102)
    if tipo_doc == "tutela":
        bloqueantes = [
            "entidad_accionada",
            "hechos",
            "derechos_vulnerados",
            "pretensiones"
        ]
        sensibles = [
            "direccion_entidad",
            "ciudad_de_los_hechos",
            "pruebas"
        ]
    else:  # derecho_peticion
        bloqueantes = [
            "entidad_accionada",
            "hechos",
            "pretensiones"
        ]
        sensibles = [
            "direccion_entidad",
            "ciudad_de_los_hechos",
            "pruebas"
        ]

    # Si actúa en representación, agregar campos de representado como sensibles
    if caso.actua_en_representacion:
        sensibles.extend([
            "nombre_representado",
            "relacion_representado",
            "identificacion_representado"
        ])

    # Datos del solicitante (siempre en solo lectura, desde perfil)
    datos_solicitante = [
        "nombre_solicitante",
        "identificacion_solicitante",
        "direccion_solicitante",
        "telefono_solicitante",
        "email_solicitante"
    ]

    # Evaluar qué campos están vacíos
    bloqueantes_faltantes = []
    for campo in bloqueantes:
        valor = getattr(caso, campo, None)
        if not valor or (isinstance(valor, str) and not valor.strip()):
            bloqueantes_faltantes.append(campo)

    sensibles_faltantes = []
    for campo in sensibles:
        valor = getattr(caso, campo, None)
        if not valor or (isinstance(valor, str) and not valor.strip()):
            sensibles_faltantes.append(campo)

    puede_generar = len(bloqueantes_faltantes) == 0

    return {
        "caso_id": caso_id,
        "tipo_documento": tipo_doc,
        "puede_generar": puede_generar,
        "campos_bloqueantes": bloqueantes,
        "campos_sensibles": sensibles,
        "datos_solicitante": datos_solicitante,
        "bloqueantes_faltantes": bloqueantes_faltantes,
        "sensibles_faltantes": sensibles_faltantes,
        "actua_en_representacion": caso.actua_en_representacion or False
    }


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
        logger.warning(f"⚠️ NO HAY MENSAJES EN EL CASO {caso_id}")
        logger.warning(f"   Room name: {caso.room_name}")
        logger.warning(f"   Estado actual: {caso.estado}")
        logger.warning(f"   Fecha inicio: {caso.fecha_inicio_sesion}")
        logger.warning(f"   Marcando caso como ABANDONADO...")

        # Marcar el caso como abandonado
        caso.estado = EstadoCaso.ABANDONADO
        db.commit()

        logger.info(f"✅ Caso {caso_id} marcado como ABANDONADO")
        logger.info(f"   Revisar logs del AGENTE para diagnóstico:")
        logger.info(f"   - Buscar '✅ caso_id EXTRAÍDO EXITOSAMENTE'")
        logger.info(f"   - Buscar '💾 Guardando mensaje'")
        logger.info(f"   - Buscar '✅ Mensaje guardado'")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sesión abandonada sin mensajes. Revisa los logs del agente."
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
        logger.info(f"   Tipo documento original: {datos_extraidos.get('tipo_documento', 'tutela').upper()}")
        logger.info(f"   ℹ️ DATOS DEL SOLICITANTE: Ya vienen del perfil del usuario (no se extraen)")
        logger.info(f"   Hechos: {'✅ Extraído' if datos_extraidos.get('hechos') else '❌ Vacío'}")
        logger.info(f"   Derechos vulnerados: {'✅ Extraído' if datos_extraidos.get('derechos_vulnerados') else '❌ Vacío'}")
        logger.info(f"   Entidad accionada: {'✅ ' + str(datos_extraidos.get('entidad_accionada', '')) if datos_extraidos.get('entidad_accionada') else '❌ Vacío'}")
        logger.info(f"   Dirección entidad: {'✅ Extraído' if datos_extraidos.get('direccion_entidad') else '❌ Vacío'}")
        logger.info(f"   Pretensiones: {'✅ Extraído' if datos_extraidos.get('pretensiones') else '❌ Vacío'}")
        logger.info(f"   Fundamentos: {'✅ Extraído' if datos_extraidos.get('fundamentos_derecho') else '❌ Vacío'}")
        logger.info(f"   Pruebas: {'✅ Extraído' if datos_extraidos.get('pruebas') else '❌ Vacío'}")
        logger.info(f"   Actúa en representación: {datos_extraidos.get('actua_en_representacion', False)}")
        logger.info(f"   Hubo derecho petición previo: {datos_extraidos.get('hubo_derecho_peticion_previo', False)}")

        # ⚖️ VALIDACIÓN DE SUBSIDIARIEDAD
        logger.info(f"\n⚖️ VALIDACIÓN DE SUBSIDIARIEDAD (Art. 86 C.P.):")
        tiene_perjuicio = datos_extraidos.get('tiene_perjuicio_irremediable', False)
        es_procedente = datos_extraidos.get('es_procedente_tutela', False)
        tipo_recomendado = datos_extraidos.get('tipo_documento_recomendado', 'derecho_peticion')

        logger.info(f"   Tiene perjuicio irremediable: {'✅ SÍ' if tiene_perjuicio else '❌ NO'}")
        logger.info(f"   Es procedente tutela: {'✅ SÍ' if es_procedente else '❌ NO'}")
        logger.info(f"   Tipo documento RECOMENDADO: {tipo_recomendado.upper()}")

        if not es_procedente:
            razon_improcedencia = datos_extraidos.get('razon_improcedencia', 'No especificada')
            logger.info(f"   ⚠️ RAZÓN DE IMPROCEDENCIA: {razon_improcedencia}")
            logger.info(f"   🔄 Se usará tipo: {tipo_recomendado}")
        else:
            logger.info(f"   ✅ Cumple requisitos de subsidiariedad")
            razon = datos_extraidos.get('razon_tipo_documento', '')
            logger.info(f"   📝 Razón: {razon}")

        # 🎯 NUEVA LÓGICA: Actualizar el caso con TODOS los datos extraídos
        # Incluso si están vacíos, mal formateados o incompletos
        # Las validaciones mostrarán advertencias en el formulario, pero no bloquean el auto-llenado
        campos_actualizados = []

        # ⚖️ Actualizar tipo_documento usando el RECOMENDADO (respeta subsidiariedad)
        # La IA ya validó si procede tutela o debe ser derecho de petición
        if datos_extraidos.get('tipo_documento_recomendado'):
            tipo_doc = datos_extraidos['tipo_documento_recomendado']
            tipo_anterior = caso.tipo_documento.value if caso.tipo_documento else 'ninguno'

            if tipo_doc == 'tutela':
                caso.tipo_documento = TipoDocumento.TUTELA
            elif tipo_doc == 'derecho_peticion':
                caso.tipo_documento = TipoDocumento.DERECHO_PETICION

            if tipo_anterior != tipo_doc:
                logger.info(f"   🔄 Tipo de documento cambiado: {tipo_anterior} → {tipo_doc}")

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

        # ℹ️ NOTA: Los datos del solicitante (nombre, identificación, dirección, teléfono, email)
        #          ya vienen del perfil del usuario y se auto-llenaron al crear el caso.
        #          La IA ya NO extrae estos datos.

        # 🆕 DATOS DE LA ENTIDAD (campos adicionales)
        if 'direccion_entidad' in datos_extraidos:
            caso.direccion_entidad = datos_extraidos['direccion_entidad']
            campos_actualizados.append('direccion_entidad')

        # 🆕 CIUDAD DE LOS HECHOS
        if 'ciudad_de_los_hechos' in datos_extraidos:
            caso.ciudad_de_los_hechos = datos_extraidos['ciudad_de_los_hechos']
            campos_actualizados.append('ciudad_de_los_hechos')

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

        # ⚖️ VALIDACIÓN DE SUBSIDIARIEDAD (nuevos campos)
        if 'hubo_derecho_peticion_previo' in datos_extraidos:
            caso.hubo_derecho_peticion_previo = datos_extraidos['hubo_derecho_peticion_previo']
            campos_actualizados.append('hubo_derecho_peticion_previo')

        if 'detalle_derecho_peticion_previo' in datos_extraidos:
            caso.detalle_derecho_peticion_previo = datos_extraidos['detalle_derecho_peticion_previo']
            campos_actualizados.append('detalle_derecho_peticion_previo')

        if 'tiene_perjuicio_irremediable' in datos_extraidos:
            caso.tiene_perjuicio_irremediable = datos_extraidos['tiene_perjuicio_irremediable']
            campos_actualizados.append('tiene_perjuicio_irremediable')

        if 'es_procedente_tutela' in datos_extraidos:
            caso.es_procedente_tutela = datos_extraidos['es_procedente_tutela']
            campos_actualizados.append('es_procedente_tutela')

        if 'razon_improcedencia' in datos_extraidos:
            caso.razon_improcedencia = datos_extraidos['razon_improcedencia']
            campos_actualizados.append('razon_improcedencia')

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

    # ⚖️ VALIDACIÓN DE SUBSIDIARIEDAD (Art. 86 C.P. - Decreto 2591/1991)
    # Si es tutela, DEBE cumplir requisitos de subsidiariedad
    if caso.tipo_documento and caso.tipo_documento.value == "tutela":
        logger.info(f"⚖️ Validando subsidiariedad para tutela del caso {caso_id}...")

        # Verificar si es_procedente_tutela fue evaluado y es False
        if caso.es_procedente_tutela is False:
            logger.warning(f"❌ Tutela NO procede - No cumple subsidiariedad")
            logger.warning(f"   Razón: {caso.razon_improcedencia or 'No especificada'}")
            logger.warning(f"   Hubo derecho de petición previo: {caso.hubo_derecho_peticion_previo}")
            logger.warning(f"   Tiene perjuicio irremediable: {caso.tiene_perjuicio_irremediable}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "La tutela no procede según el principio de subsidiariedad",
                    "razon": caso.razon_improcedencia or "No se cumple el requisito de subsidiariedad. Primero debe agotar el derecho de petición o demostrar perjuicio irremediable.",
                    "sugerencia": "Se recomienda presentar primero un derecho de petición a la entidad. Si no responden en 15 días o niegan sin fundamento, ahí sí procede la tutela.",
                    "hubo_derecho_peticion_previo": caso.hubo_derecho_peticion_previo or False,
                    "tiene_perjuicio_irremediable": caso.tiene_perjuicio_irremediable or False
                }
            )

        logger.info(f"✅ Tutela cumple subsidiariedad - Puede generarse")

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
            'hechos': caso.hechos,
            'ciudad_de_los_hechos': caso.ciudad_de_los_hechos,
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

        db.commit()
        db.refresh(caso)

        return caso

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando documento: {str(e)}"
        )


@router.post("/{caso_id}/simular-pago", response_model=CasoResponse)
def simular_pago(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🧪 SIMULADOR DE PAGO (DESARROLLO)

    Desbloquea el documento inmediatamente sin cobro real.
    En producción se reemplazará por integración con pasarela de pago real.

    Requisitos:
    - Caso debe tener documento generado
    - Caso debe pertenecer al usuario autenticado
    - Solo se puede desbloquear una vez
    """
    logger.info(f"🧪 POST /casos/{caso_id}/simular-pago - Usuario: {current_user.email}")

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
            detail="No hay documento generado para desbloquear"
        )

    if caso.documento_desbloqueado:
        logger.warning(f"⚠️ Documento ya estaba desbloqueado desde {caso.fecha_pago}")
        # No es error, simplemente retornamos el caso
        return caso

    # Desbloquear documento
    caso.documento_desbloqueado = True
    caso.fecha_pago = datetime.utcnow()

    db.commit()
    db.refresh(caso)

    logger.info(f"✅ Documento {caso_id} desbloqueado exitosamente")
    logger.info(f"   💰 Pago simulado - Fecha: {caso.fecha_pago}")

    return caso


@router.get("/{caso_id}/documento")
def obtener_documento(
    caso_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna el documento con preview o completo según estado de desbloqueo.

    Respuesta:
    - preview: True/False (si está bloqueado)
    - contenido: Texto visible (15% si bloqueado, 100% si desbloqueado)
    - contenido_completo_length: Longitud total del documento
    - precio: Precio ficticio (para desarrollo)
    - mensaje: Mensaje de bloqueo
    - descarga_habilitada: Si puede descargar PDF
    - fecha_pago: Fecha de desbloqueo (si aplica)
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

    documento_completo = caso.documento_generado
    longitud_total = len(documento_completo)

    # Determinar si está bloqueado
    esta_bloqueado = not caso.documento_desbloqueado

    if esta_bloqueado:
        # Mostrar solo 15% del documento
        limite = int(longitud_total * 0.15)
        # Buscar último salto de línea para no cortar palabras
        ultimo_salto = documento_completo.rfind('\n', 0, limite)
        if ultimo_salto > limite * 0.8:
            limite = ultimo_salto

        contenido_visible = documento_completo[:limite]

        return {
            "preview": True,
            "contenido": contenido_visible,
            "contenido_completo_length": longitud_total,
            "precio": 50000,  # Precio ficticio en COP
            "mensaje": "Desbloquea el documento completo para ver todo el contenido y descargarlo.",
            "descarga_habilitada": False,
            "fecha_pago": None
        }
    else:
        # Documento desbloqueado - mostrar todo
        return {
            "preview": False,
            "contenido": documento_completo,
            "contenido_completo_length": longitud_total,
            "precio": 50000,
            "mensaje": "",
            "descarga_habilitada": True,
            "fecha_pago": caso.fecha_pago.isoformat() if caso.fecha_pago else None
        }


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

    # 🔒 VALIDACIÓN DE PAYWALL
    if not caso.documento_desbloqueado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El documento está bloqueado. Debes realizar el pago para descargarlo."
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


