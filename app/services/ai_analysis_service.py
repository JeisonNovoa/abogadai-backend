"""
Servicio de análisis de calidad y validación de documentos legales generados con IA
"""
import re
from typing import Dict, List, Tuple
from openai import OpenAI
from ..core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def validar_jurisprudencia(documento: str) -> Dict:
    """
    Valida que la jurisprudencia citada en el documento sea real y relevante.

    Busca patrones como:
    - Sentencia T-XXX/XXXX
    - Sentencia C-XXX/XXXX
    - Sentencia SU-XXX/XXXX

    Args:
        documento: Texto del documento generado

    Returns:
        Dict con análisis de jurisprudencia
    """

    # Patrones de búsqueda de sentencias
    patron_sentencia = r'(Sentencia\s+([TCS]U?)-(\d+)[/-](\d{4}))'
    sentencias_encontradas = re.findall(patron_sentencia, documento, re.IGNORECASE)

    if not sentencias_encontradas:
        return {
            "sentencias_citadas": [],
            "total_sentencias": 0,
            "advertencia": "No se encontraron citas de jurisprudencia en el documento",
            "es_valido": True  # No es un error, pero se recomienda incluir
        }

    sentencias = []
    for match in sentencias_encontradas:
        sentencia_completa = match[0]
        tipo = match[1]  # T, C, SU
        numero = match[2]
        año = match[3]

        sentencias.append({
            "referencia": sentencia_completa,
            "tipo": tipo,
            "numero": numero,
            "año": año
        })

    # Usar GPT-4 para validar si las sentencias son reales y relevantes
    try:
        prompt = f"""Como experto en jurisprudencia de la Corte Constitucional de Colombia,
analiza las siguientes sentencias citadas en un documento legal:

{', '.join([s['referencia'] for s in sentencias])}

Para cada sentencia:
1. Indica si es probable que exista (basándote en el formato y año)
2. Si conoces su contenido general, indica el tema principal
3. Menciona si hay riesgo de que sea una "alucinación" de IA

IMPORTANTE: No inventes información. Si no conoces una sentencia, indícalo claramente.

Responde en formato JSON:
{{
    "sentencias": [
        {{
            "referencia": "Sentencia T-123/2020",
            "posiblemente_real": true/false,
            "tema_conocido": "descripción breve o 'desconocido'",
            "riesgo_alucinacion": "bajo/medio/alto",
            "comentario": "comentario adicional"
        }}
    ],
    "recomendacion_general": "texto"
}}
"""

        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en jurisprudencia constitucional colombiana. Ayudas a validar referencias jurisprudenciales."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Baja temperatura para respuestas más precisas
            response_format={"type": "json_object"}
        )

        import json
        validacion_gpt = json.loads(response.choices[0].message.content)

        return {
            "sentencias_citadas": sentencias,
            "total_sentencias": len(sentencias),
            "validacion_ia": validacion_gpt,
            "es_valido": True,
            "advertencia": "Verifica manualmente las sentencias citadas antes de radicar el documento"
        }

    except Exception as e:
        return {
            "sentencias_citadas": sentencias,
            "total_sentencias": len(sentencias),
            "error": f"No se pudo validar con IA: {str(e)}",
            "es_valido": True,
            "advertencia": "IMPORTANTE: Verifica manualmente todas las sentencias citadas"
        }


def analizar_calidad_documento(documento: str, datos_caso: dict, tipo_documento: str = "TUTELA") -> Dict:
    """
    Analiza la calidad del documento generado.

    Verifica:
    - Estructura completa
    - Coherencia
    - Lenguaje jurídico apropiado
    - Inclusión de todos los datos

    Args:
        documento: Documento generado
        datos_caso: Datos originales del caso
        tipo_documento: "tutela" o "derecho_peticion"

    Returns:
        Dict con análisis de calidad
    """

    if tipo_documento == "DERECHO_PETICION":
        # Prompt específico para derechos de petición
        prompt = f"""Como revisor experto de documentos legales colombianos, analiza la calidad del siguiente DERECHO DE PETICIÓN.

DOCUMENTO A ANALIZAR:
{documento[:12000]}

DATOS ORIGINALES DEL CASO:
- Solicitante: {datos_caso.get('nombre_solicitante', 'N/A')}
- Entidad destinataria: {datos_caso.get('entidad_accionada', 'N/A')}
- Hechos: {datos_caso.get('hechos', 'N/A')[:200]}...
- Peticiones: {datos_caso.get('pretensiones', 'N/A')[:200]}...

ANALIZA SEGÚN LOS CRITERIOS DE DERECHO DE PETICIÓN:
1. **Estructura**: ¿Tiene todas las secciones requeridas? (Objeto, Hechos, Fundamentos de Derecho, Peticiones, Anexos si aplica, Notificaciones)
2. **Coherencia**: ¿El documento es coherente y bien redactado?
3. **Datos**: ¿Incluye todos los datos del solicitante y la entidad destinataria?
4. **Lenguaje**: ¿Usa lenguaje formal y respetuoso apropiado para un derecho de petición?
5. **Fundamentos jurídicos**:
   - ¿Cita el Art. 23 C.P. y la Ley 1437 de 2011?
   - ¿Menciona el término de 15 días hábiles (Art. 14 Ley 1437)?
   - Si aplica, ¿cita normas especiales para sujetos de protección (menores Art. 44, adultos mayores Art. 46, personas con discapacidad Art. 47)?
6. **Peticiones numeradas y claras**:
   - ¿Las peticiones están numeradas (PRIMERO, SEGUNDO, TERCERO, etc.)?
   - ¿Son claras, específicas y accionables?
   - ¿Cada petición responde a una necesidad concreta?
7. **Completitud**: ¿El documento está listo para radicar?

Responde en formato JSON:
{{
    "puntuacion_total": 0-100,
    "estructura": {{"puntos": 0-15, "comentario": "texto"}},
    "coherencia": {{"puntos": 0-15, "comentario": "texto"}},
    "datos": {{"puntos": 0-15, "comentario": "texto"}},
    "lenguaje": {{"puntos": 0-15, "comentario": "texto"}},
    "fundamentos_juridicos": {{"puntos": 0-15, "comentario": "texto", "cita_art23": true/false, "cita_ley1437": true/false, "menciona_plazo_15dias": true/false}},
    "peticiones_numeradas": {{"puntos": 0-15, "comentario": "texto", "estan_numeradas": true/false, "son_especificas": true/false}},
    "completitud": {{"puntos": 0-10, "comentario": "texto"}},
    "problemas_encontrados": ["lista de problemas"],
    "sugerencias_mejora": ["lista de sugerencias"],
    "listo_para_radicar": true/false
}}
"""
    else:
        # Prompt específico para tutelas
        prompt = f"""Como revisor experto de documentos legales colombianos, analiza la calidad del siguiente documento de ACCIÓN DE TUTELA.

DOCUMENTO A ANALIZAR:
{documento[:12000]}

DATOS ORIGINALES DEL CASO:
- Solicitante: {datos_caso.get('nombre_solicitante', 'N/A')}
- Entidad accionada: {datos_caso.get('entidad_accionada', 'N/A')}
- Hechos: {datos_caso.get('hechos', 'N/A')[:200]}...
- Derechos vulnerados: {datos_caso.get('derechos_vulnerados', 'N/A')[:200]}...

ANALIZA SEGÚN LOS CRITERIOS DE TUTELA:
1. **Estructura**: ¿Tiene todas las secciones requeridas? (Hechos, Derechos Vulnerados, Pretensiones, Fundamentos de Derecho, Procedencia y Legitimidad, Inexistencia de Otro Mecanismo Idóneo, Pruebas, Juramento, Notificaciones)
2. **Coherencia**: ¿El documento es coherente y bien redactado?
3. **Datos**: ¿Incluye todos los datos del solicitante y la entidad accionada?
4. **Lenguaje**: ¿Usa lenguaje jurídico apropiado pero comprensible?
5. **Fundamentos**: ¿Cita correctamente artículos constitucionales y el Decreto 2591 de 1991?
6. **Procedencia**: ¿La sección de Procedencia y Legitimidad demuestra claramente por qué la tutela es procedente?
7. **Subsidiariedad**: ¿La sección de Inexistencia de Otro Mecanismo Idóneo explica adecuadamente por qué no hay otro medio de defensa o se agotaron los existentes?
8. **Completitud**: ¿El documento está listo para radicar?

Responde en formato JSON:
{{
    "puntuacion_total": 0-100,
    "estructura": {{"puntos": 0-15, "comentario": "texto"}},
    "coherencia": {{"puntos": 0-15, "comentario": "texto"}},
    "datos": {{"puntos": 0-15, "comentario": "texto"}},
    "lenguaje": {{"puntos": 0-15, "comentario": "texto"}},
    "fundamentos": {{"puntos": 0-10, "comentario": "texto"}},
    "procedencia": {{"puntos": 0-10, "comentario": "texto"}},
    "subsidiariedad": {{"puntos": 0-10, "comentario": "texto"}},
    "completitud": {{"puntos": 0-10, "comentario": "texto"}},
    "problemas_encontrados": ["lista de problemas"],
    "sugerencias_mejora": ["lista de sugerencias"],
    "listo_para_radicar": true/false
}}
"""

    try:
        # System message según el tipo de documento
        if tipo_documento == "DERECHO_PETICION":
            system_message = "Eres un revisor experto de documentos legales en Colombia. Evalúas la calidad de derechos de petición."
        else:
            system_message = "Eres un revisor experto de documentos legales en Colombia. Evalúas la calidad de acciones de tutela."

        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        import json
        analisis = json.loads(response.choices[0].message.content)

        return {
            "calidad": analisis,
            "es_valido": True
        }

    except Exception as e:
        return {
            "error": f"No se pudo analizar calidad: {str(e)}",
            "es_valido": False
        }


def analizar_fortaleza_caso(datos_caso: dict, tipo_documento: str = "TUTELA") -> Dict:
    """
    Analiza la fortaleza del caso antes de generar el documento.

    Evalúa diferentes criterios según el tipo de documento:
    - Para tutelas: procedencia, subsidiaridad, derechos fundamentales, etc.
    - Para derechos de petición: claridad de solicitud, competencia, legitimación, etc.

    Args:
        datos_caso: Datos del caso
        tipo_documento: "tutela" o "derecho_peticion"

    Returns:
        Dict con análisis de fortaleza
    """

    if tipo_documento == "DERECHO_PETICION":
        prompt = f"""Como abogado experto en derecho administrativo colombiano, analiza la fortaleza de este derecho de petición ANTES de generar el documento.

DATOS DEL CASO:

HECHOS:
{datos_caso.get('hechos', 'No proporcionados')}

PETICIONES:
{datos_caso.get('pretensiones', 'No especificadas')}

ENTIDAD DESTINATARIA:
{datos_caso.get('entidad_accionada', 'No especificada')}

FUNDAMENTOS:
{datos_caso.get('fundamentos_derecho', 'No especificados')}

ANALIZA:

1. **Claridad de la solicitud**: ¿Está claro qué se solicita a la entidad?
2. **Legitimación del peticionario**: ¿El solicitante tiene interés legítimo?
3. **Competencia de la entidad**: ¿Es la entidad correcta para atender esta petición?
4. **Hechos claros**: ¿Los hechos están bien descritos y son relevantes?
5. **Especificidad**: ¿La petición es específica y accionable?
6. **Fundamentos**: ¿Se mencionan los fundamentos legales (Art. 23 C.P., Ley 1437)?

Responde en formato JSON:
{{
    "fortaleza_total": 0-100,
    "probabilidad_exito": "baja/media/alta",
    "claridad_solicitud": {{"puntos": 0-20, "comentario": "texto"}},
    "legitimacion": {{"puntos": 0-20, "comentario": "texto"}},
    "competencia_entidad": {{"puntos": 0-20, "comentario": "texto"}},
    "claridad_hechos": {{"puntos": 0-15, "comentario": "texto"}},
    "especificidad": {{"puntos": 0-15, "comentario": "texto"}},
    "fundamentos": {{"puntos": 0-10, "comentario": "texto"}},
    "puntos_fuertes": ["lista de fortalezas del caso"],
    "puntos_debiles": ["lista de debilidades"],
    "recomendaciones": ["lista de recomendaciones para mejorar"],
    "advertencias": ["advertencias importantes"],
    "debe_proceder": true/false,
    "razon_no_proceder": "texto si no debe proceder"
}}
"""
    else:
        prompt = f"""Como abogado constitucionalista experto, analiza la fortaleza de este caso de acción de tutela ANTES de generar el documento.

DATOS DEL CASO:

HECHOS:
{datos_caso.get('hechos', 'No proporcionados')}

DERECHOS VULNERADOS:
{datos_caso.get('derechos_vulnerados', 'No especificados')}

PRETENSIONES:
{datos_caso.get('pretensiones', 'No especificadas')}

ENTIDAD ACCIONADA:
{datos_caso.get('entidad_accionada', 'No especificada')}

IMPORTANTE - VERIFICAR TIPO DE DOCUMENTO CORRECTO:
Antes de analizar, evalúa si TUTELA es el mecanismo apropiado o si debería ser DERECHO DE PETICIÓN:
- Si NO hubo derecho de petición previo Y no hay urgencia extrema → debería ser DERECHO DE PETICIÓN primero
- Si YA hubo derecho de petición Y (no respondieron O negaron O no resolvieron) → TUTELA es apropiada
- Si hay urgencia extrema o perjuicio irremediable → TUTELA es apropiada directamente

ANALIZA:

1. **Procedencia de la tutela**: ¿Es el mecanismo apropiado para este caso?
2. **Derechos fundamentales**: ¿Hay vulneración clara de derechos fundamentales?
3. **Subsidiaridad**: ¿Se demuestra que no hay otro medio de defensa o hay perjuicio irremediable?
4. **Legitimación**: ¿La entidad accionada es la correcta?
5. **Hechos**: ¿Los hechos están claros y son suficientes?
6. **Inmediatez**: ¿Los hechos son recientes? (plazo razonable)

Responde en formato JSON:
{{
    "fortaleza_total": 0-100,
    "probabilidad_exito": "baja/media/alta",
    "es_tipo_documento_correcto": true/false,
    "sugerencia_tipo_documento": "tutela o derecho_peticion si es_tipo_documento_correcto es false",
    "razon_sugerencia": "explicación de por qué debería ser otro tipo de documento, si aplica",
    "procedencia_tutela": {{"puntos": 0-20, "comentario": "texto", "es_procedente": true/false}},
    "derechos_fundamentales": {{"puntos": 0-20, "comentario": "texto"}},
    "subsidiaridad": {{"puntos": 0-20, "comentario": "texto"}},
    "legitimacion": {{"puntos": 0-15, "comentario": "texto"}},
    "claridad_hechos": {{"puntos": 0-15, "comentario": "texto"}},
    "inmediatez": {{"puntos": 0-10, "comentario": "texto"}},
    "puntos_fuertes": ["lista de fortalezas del caso"],
    "puntos_debiles": ["lista de debilidades"],
    "recomendaciones": ["lista de recomendaciones para mejorar el caso"],
    "advertencias": ["advertencias importantes"],
    "debe_proceder": true/false,
    "razon_no_proceder": "texto si no debe proceder"
}}
"""

    try:
        system_message = "Eres un abogado constitucionalista experto que evalúa la viabilidad de acciones de tutela en Colombia." if tipo_documento == "TUTELA" else "Eres un abogado experto en derecho administrativo colombiano que evalúa la viabilidad de derechos de petición."

        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        import json
        analisis = json.loads(response.choices[0].message.content)

        # Calcular probabilidad numérica
        fortaleza = analisis.get('fortaleza_total', 0)
        if fortaleza >= 80:
            probabilidad_porcentaje = "75-90%"
        elif fortaleza >= 60:
            probabilidad_porcentaje = "50-75%"
        elif fortaleza >= 40:
            probabilidad_porcentaje = "30-50%"
        else:
            probabilidad_porcentaje = "10-30%"

        analisis['probabilidad_porcentaje'] = probabilidad_porcentaje

        return {
            "fortaleza": analisis,
            "es_valido": True
        }

    except Exception as e:
        return {
            "error": f"No se pudo analizar fortaleza: {str(e)}",
            "es_valido": False
        }


def generar_sugerencias_mejora(documento: str, analisis_calidad: dict, analisis_jurisprudencia: dict) -> Dict:
    """
    Genera sugerencias específicas para mejorar el documento.

    Args:
        documento: Documento generado
        analisis_calidad: Resultado del análisis de calidad
        analisis_jurisprudencia: Resultado del análisis de jurisprudencia

    Returns:
        Dict con sugerencias de mejora
    """

    sugerencias = []

    # Sugerencias basadas en calidad
    if analisis_calidad.get('es_valido'):
        calidad = analisis_calidad.get('calidad', {})

        if calidad.get('puntuacion_total', 0) < 70:
            sugerencias.append({
                "categoria": "Calidad General",
                "prioridad": "alta",
                "descripcion": "El documento tiene una calidad inferior al 70%. Revisa las sugerencias específicas.",
                "accion": "Revisar y mejorar el documento antes de radicar"
            })

        if calidad.get('problemas_encontrados'):
            for problema in calidad['problemas_encontrados'][:3]:  # Top 3 problemas
                sugerencias.append({
                    "categoria": "Problema Detectado",
                    "prioridad": "alta",
                    "descripcion": problema,
                    "accion": "Corregir antes de radicar"
                })

    # Sugerencias basadas en jurisprudencia
    if analisis_jurisprudencia.get('es_valido'):
        total_sentencias = analisis_jurisprudencia.get('total_sentencias', 0)

        if total_sentencias == 0:
            sugerencias.append({
                "categoria": "Jurisprudencia",
                "prioridad": "media",
                "descripcion": "No se citaron sentencias de la Corte Constitucional",
                "accion": "Considera agregar jurisprudencia relevante para fortalecer el caso"
            })
        elif total_sentencias > 0:
            validacion = analisis_jurisprudencia.get('validacion_ia', {})
            if validacion.get('sentencias'):
                for sent in validacion['sentencias']:
                    if sent.get('riesgo_alucinacion') == 'alto':
                        sugerencias.append({
                            "categoria": "Jurisprudencia",
                            "prioridad": "crítica",
                            "descripcion": f"Sentencia {sent['referencia']} tiene alto riesgo de ser inventada",
                            "accion": "Verificar en bases de datos oficiales o eliminar"
                        })

    return {
        "sugerencias": sugerencias,
        "total_sugerencias": len(sugerencias),
        "prioridad_critica": len([s for s in sugerencias if s['prioridad'] == 'crítica']),
        "prioridad_alta": len([s for s in sugerencias if s['prioridad'] == 'alta']),
        "prioridad_media": len([s for s in sugerencias if s['prioridad'] == 'media'])
    }


def analisis_completo_documento(documento: str, datos_caso: dict, tipo_documento: str = "TUTELA") -> Dict:
    """
    Realiza un análisis completo del documento generado.

    Args:
        documento: Documento generado
        datos_caso: Datos originales del caso
        tipo_documento: "tutela" o "derecho_peticion"

    Returns:
        Dict con análisis completo
    """

    # 1. Validar jurisprudencia
    validacion_jurisprudencia = validar_jurisprudencia(documento)

    # 2. Analizar calidad (pasando el tipo de documento)
    analisis_calidad = analizar_calidad_documento(documento, datos_caso, tipo_documento)

    # 3. Generar sugerencias
    sugerencias = generar_sugerencias_mejora(documento, analisis_calidad, validacion_jurisprudencia)

    # Determinar si el documento está listo
    listo_para_radicar = True
    razones_no_listo = []

    if analisis_calidad.get('es_valido'):
        calidad = analisis_calidad.get('calidad', {})
        if calidad.get('puntuacion_total', 0) < 60:
            listo_para_radicar = False
            razones_no_listo.append("Calidad del documento inferior al 60%")

        if not calidad.get('listo_para_radicar', True):
            listo_para_radicar = False
            razones_no_listo.append("El análisis de calidad indica que no está listo")

    if sugerencias.get('prioridad_critica', 0) > 0:
        listo_para_radicar = False
        razones_no_listo.append("Hay sugerencias de prioridad crítica sin resolver")

    return {
        "jurisprudencia": validacion_jurisprudencia,
        "calidad": analisis_calidad,
        "sugerencias": sugerencias,
        "listo_para_radicar": listo_para_radicar,
        "razones_no_listo": razones_no_listo,
        "resumen": {
            "puntuacion_calidad": analisis_calidad.get('calidad', {}).get('puntuacion_total', 0) if analisis_calidad.get('es_valido') else 0,
            "sentencias_citadas": validacion_jurisprudencia.get('total_sentencias', 0),
            "sugerencias_criticas": sugerencias.get('prioridad_critica', 0),
            "sugerencias_altas": sugerencias.get('prioridad_alta', 0),
            "recomendacion": "Listo para radicar" if listo_para_radicar else "Requiere revisión antes de radicar"
        }
    }
