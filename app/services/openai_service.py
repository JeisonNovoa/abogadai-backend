from openai import OpenAI
from ..core.config import settings
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generar_tutela(datos_caso: dict) -> str:
    """
    Genera un documento de tutela completo usando GPT-4
    """

    prompt = f"""Eres un abogado experto en derecho constitucional colombiano especializado en acciones de tutela.

Genera un documento de ACCIÓN DE TUTELA completo, formal y profesional siguiendo la estructura legal colombiana.

DATOS DEL CASO:

SOLICITANTE:
- Nombre: {datos_caso.get('nombre_solicitante', '')}
- Identificación: {datos_caso.get('identificacion_solicitante', '')}
- Dirección: {datos_caso.get('direccion_solicitante', '')}
- Teléfono: {datos_caso.get('telefono_solicitante', '')}
- Email: {datos_caso.get('email_solicitante', '')}
- Actúa en representación: {'Sí' if datos_caso.get('actua_en_representacion', False) else 'No'}
{f'''- Persona representada: {datos_caso.get('nombre_representado', '')}
- Identificación representado: {datos_caso.get('identificacion_representado', '')}
- Relación: {datos_caso.get('relacion_representado', '')}
- Tipo de persona representada: {datos_caso.get('tipo_representado', '')}''' if datos_caso.get('actua_en_representacion', False) else ''}

ENTIDAD ACCIONADA:
- Nombre: {datos_caso.get('entidad_accionada', '')}
- Dirección: {datos_caso.get('direccion_entidad', '')}
- Representante Legal: {datos_caso.get('representante_legal', '')}

HECHOS:
{datos_caso.get('hechos', '')}

DERECHOS VULNERADOS:
{datos_caso.get('derechos_vulnerados', '')}

PRETENSIONES:
{datos_caso.get('pretensiones', '')}

FUNDAMENTOS DE DERECHO:
{datos_caso.get('fundamentos_derecho', '')}

PRUEBAS Y DOCUMENTOS ANEXOS:
{datos_caso.get('pruebas', 'No se especificaron pruebas')}

INSTRUCCIONES:
1. Genera un documento formal de tutela con encabezado dirigido al Juez competente

2. Si el solicitante actúa en representación de otra persona:
   - Indica claramente en el encabezado quién firma y en qué calidad (madre, padre, cuidador, apoderado, etc.)
   - Explica quién es la persona cuyos derechos están siendo vulnerados
   - En la sección de PROCEDENCIA Y LEGITIMIDAD, justifica por qué tiene legitimidad para actuar

3. ESTRUCTURA REQUERIDA (en este orden):
   - I. HECHOS: Narrativa clara y cronológica de los hechos que fundamentan la acción
   - II. DERECHOS VULNERADOS: Identificación explícita de los derechos fundamentales vulnerados con sus artículos constitucionales
   - III. PRETENSIONES: Lo que se solicita que ordene el juez de manera clara y específica
   - IV. FUNDAMENTOS DE DERECHO: Base jurídica constitucional (Art. 86 C.P. y Decreto 2591 de 1991)
   - V. PROCEDENCIA Y LEGITIMIDAD: Explica por qué la tutela es procedente en este caso concreto, citando el Decreto 2591 de 1991 y la jurisprudencia aplicable. Demuestra la legitimación en la causa (quién presenta y por qué tiene derecho a hacerlo). Si actúa en representación, justifica la legitimidad (ej: para menores, el padre/madre tiene legitimidad; para adultos mayores dependientes, el cuidador; etc.)
   - VI. INEXISTENCIA DE OTRO MECANISMO IDÓNEO: Explica qué otros medios ya se usaron (derecho de petición, quejas internas, etc.) y por qué no fueron suficientes, o por qué no existe otro mecanismo de defensa judicial eficaz. Si hay perjuicio irremediable o urgencia, menciónalo aquí
   - VII. PRUEBAS: Enumeración de las pruebas que se anexan o se solicitarán. USA EXACTAMENTE la información proporcionada en "PRUEBAS Y DOCUMENTOS ANEXOS" arriba. Si no se especificaron pruebas, indica que se aportarán oportunamente
   - VIII. JURAMENTO: Manifestación bajo juramento de no haber presentado otra tutela por los mismos hechos
   - IX. NOTIFICACIONES: Dirección física y correo electrónico para notificaciones

4. Usa lenguaje jurídico apropiado pero comprensible

5. Cita artículos constitucionales relevantes (ej: Art. 11, 13, 15, 16, 20, 48, 49, etc. según corresponda)

6. Las PRETENSIONES deben solicitar órdenes específicas al juez (no son "peticiones" como en un derecho de petición)

7. En la sección V (PROCEDENCIA Y LEGITIMIDAD), explica claramente por qué se cumplen los requisitos de procedibilidad de la tutela

8. En la sección VI (INEXISTENCIA DE OTRO MECANISMO IDÓNEO), demuestra la subsidiariedad de la acción explicando los intentos previos o la urgencia del caso

9. Asegúrate de que el documento sea completo y listo para radicar

IMPORTANTE SOBRE JURISPRUDENCIA:
- SOLO cita jurisprudencia si estás COMPLETAMENTE SEGURO de que existe
- Si no estás seguro de una sentencia específica, NO LA CITES
- Es mejor NO citar jurisprudencia que citar sentencias inventadas
- Si citas, usa SOLO sentencias muy conocidas y emblemáticas de la Corte Constitucional
- Puedes mencionar "según jurisprudencia reiterada de la Corte Constitucional" sin número específico
- NUNCA inventes números de sentencias

El documento debe estar listo para ser presentado ante un juez de la República de Colombia."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un abogado constitucionalista experto en Colombia. Generas documentos legales formales, completos y profesionales."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Temperatura baja para máxima estabilidad en documentos jurídicos
            max_completion_tokens=4000
        )

        documento_generado = response.choices[0].message.content
        return documento_generado

    except Exception as e:
        raise Exception(f"Error generando tutela con OpenAI: {str(e)}")


def generar_derecho_peticion(datos_caso: dict) -> str:
    """
    Genera un documento de derecho de petición usando GPT-4
    """

    prompt = f"""Eres un abogado experto en derecho administrativo colombiano especializado en derechos de petición.

Genera un documento de DERECHO DE PETICIÓN completo, formal y profesional siguiendo la estructura legal colombiana.

DATOS DEL CASO:

SOLICITANTE:
- Nombre: {datos_caso.get('nombre_solicitante', '')}
- Identificación: {datos_caso.get('identificacion_solicitante', '')}
- Dirección: {datos_caso.get('direccion_solicitante', '')}
- Teléfono: {datos_caso.get('telefono_solicitante', '')}
- Email: {datos_caso.get('email_solicitante', '')}
- Actúa en representación: {'Sí' if datos_caso.get('actua_en_representacion', False) else 'No'}
{f'''- Persona representada: {datos_caso.get('nombre_representado', '')}
- Identificación representado: {datos_caso.get('identificacion_representado', '')}
- Relación: {datos_caso.get('relacion_representado', '')}
- Tipo de persona representada: {datos_caso.get('tipo_representado', '')}''' if datos_caso.get('actua_en_representacion', False) else ''}

ENTIDAD DESTINATARIA:
- Nombre: {datos_caso.get('entidad_accionada', '')}
- Dirección: {datos_caso.get('direccion_entidad', '')}
- Representante Legal: {datos_caso.get('representante_legal', '')}

HECHOS:
{datos_caso.get('hechos', '')}

PETICIONES:
{datos_caso.get('pretensiones', '')}

FUNDAMENTOS DE DERECHO:
{datos_caso.get('fundamentos_derecho', '')}

PRUEBAS Y DOCUMENTOS ANEXOS:
{datos_caso.get('pruebas', 'No se especificaron documentos anexos')}

INSTRUCCIONES:
1. Genera un documento formal de derecho de petición con encabezado apropiado dirigido a la entidad destinataria

2. ESTRUCTURA REQUERIDA (en este orden):
   - I. OBJETO: Presentar la naturaleza de la petición de manera clara y directa
   - II. HECHOS: Relatar los hechos cronológicamente y de forma clara
   - III. FUNDAMENTOS DE DERECHO:
     * SIEMPRE citar el Art. 23 de la Constitución Política de Colombia
     * SIEMPRE citar la Ley 1437 de 2011 (Código de Procedimiento Administrativo y de lo Contencioso Administrativo)
     * Si involucra menores de edad: citar el Art. 44 C.P. (derechos fundamentales de los niños) y mencionar el interés superior del menor
     * Si involucra adultos mayores: citar el Art. 46 C.P. (protección especial a la tercera edad)
     * Si involucra personas con discapacidad: citar el Art. 47 C.P. (protección y atención especial)
     * Redactar un párrafo jurídico sólido que conecte estas normas con el caso
   - IV. PETICIONES: Enumerar NUMERADAS (PRIMERO, SEGUNDO, TERCERO, etc.) de forma clara, específica y accionable lo que se solicita a la entidad. Cada petición debe responder a una necesidad concreta del solicitante
   - V. ANEXOS: Si se especificaron pruebas o documentos anexos, USA EXACTAMENTE la información proporcionada en "PRUEBAS Y DOCUMENTOS ANEXOS" arriba. Si no se especificaron, omite esta sección o indica que se aportarán posteriormente
   - VI. NOTIFICACIONES: Indicar dirección física y correo electrónico para notificaciones

3. En los FUNDAMENTOS DE DERECHO:
   - Incluye un párrafo explicando el derecho de petición como derecho fundamental
   - Menciona EXPRESAMENTE:
     * Término de 15 días hábiles (Art. 14 Ley 1437) para responder peticiones generales
     * Término de 10 días hábiles (Art. 14 Ley 1437) cuando se solicitan documentos o información específica
     * Usa el término correcto según el tipo de petición del caso
   - Si es sujeto de especial protección (menor, adulto mayor, persona con discapacidad), enfatiza la obligación reforzada del Estado

4. En las PETICIONES:
   - USA el formato: "PRIMERO:", "SEGUNDO:", "TERCERO:", etc.
   - Cada petición debe ser específica, medible y accionable
   - No mezcles múltiples solicitudes en una sola petición

5. Usa lenguaje formal, respetuoso y técnico apropiado para un derecho de petición

6. IMPORTANTE - NO uses terminología de acción de tutela:
   - NO uses: "accionante", "accionado", "juez", "sentencia", "fallo", "pretensiones", "amparo"
   - USA: "peticionario", "entidad destinataria", "respuesta", "peticiones", "solicitud"

7. El documento debe estar completo y listo para radicar

El documento debe estar listo para ser presentado ante la entidad correspondiente en Colombia."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un abogado experto en derecho administrativo en Colombia. Generas documentos legales formales, completos y profesionales."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Temperatura baja para máxima estabilidad en documentos jurídicos
            max_completion_tokens=3000
        )

        documento_generado = response.choices[0].message.content
        return documento_generado

    except Exception as e:
        raise Exception(f"Error generando derecho de petición con OpenAI: {str(e)}")


def extraer_datos_conversacion(mensajes: list) -> dict:
    """
    Extrae información estructurada de una conversación entre usuario y asistente legal

    Args:
        mensajes: Lista de diccionarios con formato:
                  [{"remitente": "usuario|asistente", "texto": "...", "timestamp": "..."}]

    Returns:
        dict con los campos extraídos: tipo_documento, razon_tipo_documento, hechos,
        derechos_vulnerados, entidad_accionada, pretensiones, fundamentos_derecho, pruebas,
        actua_en_representacion, nombre_representado, identificacion_representado,
        relacion_representado, tipo_representado, hubo_derecho_peticion_previo,
        detalle_derecho_peticion_previo
    """

    # Construir la conversación en formato legible
    conversacion_texto = ""
    for msg in mensajes:
        remitente = "ASISTENTE" if msg["remitente"] == "asistente" else "USUARIO"
        conversacion_texto += f"{remitente}: {msg['texto']}\n\n"

    prompt = f"""Eres un asistente legal experto en derecho constitucional y administrativo colombiano.

Analiza la siguiente conversación entre un usuario y un asistente legal que está recopilando información para crear un documento legal.

CONVERSACIÓN:
{conversacion_texto}

TAREA:
Extrae y estructura la siguiente información en formato JSON. LEE CUIDADOSAMENTE toda la conversación y extrae TODOS los datos mencionados, especialmente los datos personales del solicitante.

IMPORTANTE - DATOS PERSONALES DEL SOLICITANTE:
Busca activamente en la conversación:
- El nombre completo del solicitante (cuando dice "me llamo...", "mi nombre es...", "soy...")
- Su número de cédula o documento (cuando dice "mi cédula es...", "mi documento es...")
- Su dirección completa (cuando dice "vivo en...", "mi dirección es...", "mi dirección completa es...")
- Su número de teléfono (cuando dice "mi teléfono es...", "mi celular es...")
- Su correo electrónico (cuando dice "mi correo es...", "mi email es...")

1. **tipo_documento**: Determina el tipo de documento legal apropiado según la conversación.

   REGLAS DE DECISIÓN (APLICAR EN ESTE ORDEN):

   A. DERECHO DE PETICIÓN primero si NO hubo derecho de petición previo Y:
      - Se busca obtener información de una entidad
      - Se solicita un servicio que debería ser provisto
      - Se presenta una queja o reclamo administrativo
      - El caso NO tiene urgencia extrema ni perjuicio irremediable
      → En estos casos, sugiere "derecho_peticion" como primer paso

   B. TUTELA si:
      - YA hubo derecho de petición previo Y (no respondieron O negaron la solicitud O la respuesta no resolvió el problema)
      - O hay urgencia extrema / perjuicio irremediable (ej: salud en riesgo inmediato, vida en peligro)
      - O se vulneran derechos fundamentales Y no hay otro mecanismo de defensa judicial eficaz
      → En estos casos, sugiere "tutela"

   CRITERIOS ADICIONALES:
   - TUTELA: Derechos fundamentales vulnerados (salud, vida, educación, debido proceso, etc.), requiere orden judicial, subsidiariedad o perjuicio irremediable
   - DERECHO DE PETICIÓN: Solicitud de información, trámites administrativos, quejas, reclamos, petición de servicios, primer mecanismo a agotar

2. **nombre_solicitante**: El nombre completo de la persona que presenta el caso.
   Busca en la conversación cuando la persona dice: "me llamo...", "mi nombre es...", "soy...", o cuando Sofía confirma el nombre.
   Extrae el nombre EXACTAMENTE como lo dice el usuario.
   Si no lo menciona, deja este campo vacío.

3. **identificacion_solicitante**: El número de cédula o documento de identidad.
   Busca cuando dice: "mi cédula es...", "mi documento es...", "mi número de identificación es...".
   Convierte números en palabras a dígitos (ej: "cincuenta y dos punto trescientos cuarenta y cinco punto sesenta y ocho" → "52345678").
   Remueve puntos y espacios, solo dígitos.
   Si no lo menciona, deja este campo vacío.

4. **direccion_solicitante**: La dirección completa del solicitante para notificaciones.
   Busca cuando dice: "vivo en...", "mi dirección es...", "mi dirección completa es...".
   Incluye calle, número, ciudad.
   Si no lo menciona, deja este campo vacío.

5. **telefono_solicitante**: El número de teléfono o celular del solicitante.
   Busca cuando dice: "mi teléfono es...", "mi celular es...", "mi número es...".
   Convierte a dígitos sin espacios ni guiones (ej: "300-123-456" → "300123456").
   Si no lo menciona, deja este campo vacío.

6. **email_solicitante**: El correo electrónico del solicitante.
   Busca cuando dice: "mi correo es...", "mi email es...", "mi correo electrónico es...".
   Extrae el email completo.
   Si no lo menciona, deja este campo vacío.

7. **hechos**: Narrativa cronológica y detallada de los hechos.
   Redacta en tercera persona, estilo legal, usando el nombre del solicitante si está disponible.
   Si no hay información suficiente, deja este campo vacío.

8. **derechos_vulnerados**: (Solo para tutelas) Lista de derechos fundamentales vulnerados con sus artículos constitucionales.
   Formato: "Derecho a la Salud (Art. 49 C.P.), Derecho a la Vida (Art. 11 C.P.)"
   Si es derecho de petición o no hay información suficiente, deja este campo vacío.

9. **entidad_accionada**: Nombre completo de la entidad, empresa o institución.
   Debe ser el nombre oficial completo (ejemplo: "EPS Sanitas S.A.", "Ministerio de Salud").
   Si no hay información suficiente, deja este campo vacío.

10. **direccion_entidad**: La dirección de la sede de la entidad accionada.
    Busca cuando dice: "la dirección de la EPS es...", "la sede está en...", "está ubicada en...".
    Si no lo menciona, deja este campo vacío.

11. **pretensiones**: Lo que solicita el usuario.
    - Para tutelas: Qué solicita que ordene el juez
    - Para derechos de petición: Qué información o actuación solicita
    Si no hay información suficiente, deja este campo vacío.

12. **fundamentos_derecho**: Leyes, decretos o jurisprudencia aplicable mencionada en la conversación.
    Solo incluye lo que fue EXPLÍCITAMENTE mencionado. Si nada fue mencionado, deja este campo vacío.

13. **pruebas**: Documentos, pruebas o anexos mencionados en la conversación.
    Incluye: diagnósticos médicos, fórmulas, fotografías, derechos de petición previos, certificaciones, etc.
    Enumera cada documento mencionado de forma clara. Si no hay información suficiente, deja este campo vacío.

14. **actua_en_representacion**: (Booleano) true si el solicitante actúa en representación de otra persona, false si actúa en nombre propio.
    Detecta frases como "mi hijo", "mi madre", "represento a", "en nombre de", etc.

15. **nombre_representado**: (Solo si actúa en representación) Nombre completo de la persona representada.
    Si no hay información suficiente, deja este campo vacío.

16. **identificacion_representado**: (Solo si actúa en representación) Documento de identidad de la persona representada.
    Si no hay información suficiente, deja este campo vacío.

17. **relacion_representado**: (Solo si actúa en representación) Relación entre el solicitante y el representado.
    Ejemplo: "madre", "padre", "apoderado", "tutor legal", "cuidador", etc.
    Si no hay información suficiente, deja este campo vacío.

18. **tipo_representado**: (Solo si actúa en representación) Tipo de persona representada.
    Opciones: "menor_edad", "adulto_mayor", "persona_discapacidad", "otro"
    Determina esto según el contexto de la conversación.
    Si no hay información suficiente, deja este campo vacío.

19. **hubo_derecho_peticion_previo**: (Booleano) true si en la conversación se menciona que ya hubo un derecho de petición previo (presentado, radicado, enviado), false si no se menciona o no hubo.
    Esto es importante para determinar si procede directamente una tutela por subsidiariedad.

20. **detalle_derecho_peticion_previo**: (Solo si hubo derecho de petición previo) Detalles sobre el derecho de petición previo.
    Incluye: fecha de radicación, entidad a la que se dirigió, qué se solicitó, respuesta obtenida (si la hubo), razón por la que no resolvió el problema.
    Si no hay información suficiente, deja este campo vacío.

INSTRUCCIONES IMPORTANTES:
- ⚠️ PRIORIDAD MÁXIMA: Extrae TODOS los datos personales del solicitante (nombre, cédula, dirección, teléfono, email) que se mencionen en la conversación
- Lee TODA la conversación completa antes de extraer, los datos pueden estar en cualquier parte
- Si algún campo no tiene información suficiente en la conversación, devuélvelo como cadena vacía ""
- Mantén lenguaje legal apropiado para Colombia
- Redacta los hechos de forma coherente y cronológica
- Sé preciso con los artículos constitucionales (usa "Art. XX C.P.")
- NO inventes información que no esté en la conversación
- NO cites jurisprudencia a menos que haya sido mencionada explícitamente
- IMPORTANTE: Determina correctamente el tipo_documento basándote en el contexto de la conversación
- Convierte números en palabras a dígitos (ej: "cincuenta y dos" → "52")

FORMATO DE SALIDA:
Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta, sin markdown ni texto adicional.
ASEGÚRATE de incluir TODOS los campos, especialmente los datos personales del solicitante:
{{
    "tipo_documento": "tutela" o "derecho_peticion",
    "razon_tipo_documento": "explicación breve de por qué se eligió tutela o derecho de petición",
    "nombre_solicitante": "nombre completo del solicitante o cadena vacía",
    "identificacion_solicitante": "número de cédula solo dígitos o cadena vacía",
    "direccion_solicitante": "dirección completa o cadena vacía",
    "telefono_solicitante": "teléfono solo dígitos o cadena vacía",
    "email_solicitante": "correo electrónico o cadena vacía",
    "hechos": "narrativa de los hechos o cadena vacía",
    "derechos_vulnerados": "derechos con artículos o cadena vacía",
    "entidad_accionada": "nombre de la entidad o cadena vacía",
    "direccion_entidad": "dirección de la entidad o cadena vacía",
    "pretensiones": "lo que se solicita o cadena vacía",
    "fundamentos_derecho": "fundamentos legales o cadena vacía",
    "pruebas": "lista de documentos/pruebas o cadena vacía",
    "actua_en_representacion": true o false,
    "nombre_representado": "nombre del representado o cadena vacía",
    "identificacion_representado": "cédula del representado o cadena vacía",
    "relacion_representado": "relación con el representado o cadena vacía",
    "tipo_representado": "tipo de representado o cadena vacía",
    "hubo_derecho_peticion_previo": true o false,
    "detalle_derecho_peticion_previo": "detalles del derecho de petición previo o cadena vacía"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1-2025-11-13",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente legal experto en derecho constitucional colombiano. Extraes información de conversaciones y la estructuras en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Baja temperatura para mayor precisión
            max_completion_tokens=2000,
            response_format={"type": "json_object"}  # Forzar respuesta JSON
        )

        resultado_texto = response.choices[0].message.content

        # Parsear el JSON
        datos_extraidos = json.loads(resultado_texto)

        # Validar que tenga las claves esperadas
        campos_esperados = [
            "tipo_documento", "razon_tipo_documento", "hechos", "derechos_vulnerados",
            "entidad_accionada", "pretensiones", "fundamentos_derecho", "pruebas",
            "actua_en_representacion", "nombre_representado", "identificacion_representado",
            "relacion_representado", "tipo_representado", "hubo_derecho_peticion_previo",
            "detalle_derecho_peticion_previo"
        ]
        for campo in campos_esperados:
            if campo not in datos_extraidos:
                if campo == "tipo_documento":
                    datos_extraidos[campo] = "tutela"  # Valor por defecto
                elif campo in ["actua_en_representacion", "hubo_derecho_peticion_previo"]:
                    datos_extraidos[campo] = False  # Valor por defecto para booleanos
                else:
                    datos_extraidos[campo] = ""

        # Validar que tipo_documento tenga un valor válido
        if datos_extraidos["tipo_documento"] not in ["tutela", "derecho_peticion"]:
            datos_extraidos["tipo_documento"] = "tutela"  # Fallback a tutela si el valor no es válido

        return datos_extraidos

    except json.JSONDecodeError as e:
        raise Exception(f"Error al parsear respuesta JSON de OpenAI: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extrayendo datos de conversación con OpenAI: {str(e)}")
