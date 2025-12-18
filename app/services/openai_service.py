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

HECHOS:
{datos_caso.get('hechos', '')}

CIUDAD DONDE OCURRIERON LOS HECHOS:
{datos_caso.get('ciudad_de_los_hechos', '')}

DERECHOS VULNERADOS:
{datos_caso.get('derechos_vulnerados', '')}

PRETENSIONES:
{datos_caso.get('pretensiones', '')}

FUNDAMENTOS DE DERECHO:
{datos_caso.get('fundamentos_derecho', '')}

PRUEBAS Y DOCUMENTOS ANEXOS:
{datos_caso.get('pruebas', 'No se especificaron pruebas')}

INSTRUCCIONES PARA FORMATO PROFESIONAL:

1. ENCABEZADO FORMAL:
   Inicia el documento con este formato exacto:

   **ACCIÓN DE TUTELA**

   Señor
   JUEZ COMPETENTE
   REPARTO TUTELAS
   Ciudad

   REFERENCIA: Acción de Tutela
   ACCIONANTE: [Nombre completo del solicitante]
   ACCIONADO: [Nombre de la entidad]

   [Nombre completo del solicitante], identificado(a) como aparece al pie de mi firma, {f'actuando en calidad de {datos_caso.get("relacion_representado", "representante legal")} de {datos_caso.get("nombre_representado", "")},' if datos_caso.get('actua_en_representacion', False) else 'actuando en nombre propio,'} me permito presentar ACCIÓN DE TUTELA contra [entidad], con fundamento en los artículos 86 de la Constitución Política de Colombia y el Decreto 2591 de 1991, con base en los siguientes:

2. Si el solicitante actúa en representación de otra persona:
   - Indica claramente en el encabezado quién firma y en qué calidad (madre, padre, cuidador, apoderado, etc.)
   - Explica quién es la persona cuyos derechos están siendo vulnerados
   - En la sección de PROCEDENCIA Y LEGITIMIDAD, justifica por qué tiene legitimidad para actuar

3. ESTRUCTURA REQUERIDA (usar NUMERACIÓN ROMANA):

   **I. HECHOS**
   Narrativa clara y cronológica de los hechos que fundamentan la acción. Numera los hechos si son varios.

   **II. DERECHOS FUNDAMENTALES VULNERADOS**
   Identificación explícita de los derechos fundamentales vulnerados con sus artículos constitucionales.
   Formato: "- Derecho a... (Artículo XX de la Constitución Política)"

   **III. PRETENSIONES**
   Lo que se solicita que ordene el juez de manera clara y específica.
   Usar formato: "PRIMERA:", "SEGUNDA:", "TERCERA:", etc.

   **IV. FUNDAMENTOS DE DERECHO**
   Base jurídica constitucional (Art. 86 C.P. y Decreto 2591 de 1991).

   **V. PROCEDENCIA Y LEGITIMIDAD**
   Explica por qué la tutela es procedente en este caso concreto, citando el Decreto 2591 de 1991 y la jurisprudencia aplicable.
   Demuestra la legitimación en la causa (quién presenta y por qué tiene derecho a hacerlo).
   Si actúa en representación, justifica la legitimidad (ej: para menores, el padre/madre tiene legitimidad; para adultos mayores dependientes, el cuidador; etc.)

   **VI. INEXISTENCIA DE OTRO MECANISMO DE DEFENSA JUDICIAL**
   Explica qué otros medios ya se usaron (derecho de petición, quejas internas, etc.) y por qué no fueron suficientes, o por qué no existe otro mecanismo de defensa judicial eficaz.
   Si hay perjuicio irremediable o urgencia, menciónalo aquí.

   **VII. PRUEBAS Y ANEXOS**
   Enumeración formal de las pruebas que se anexan.
   Formato: "- Anexo 1: [descripción]"
   USA EXACTAMENTE la información proporcionada en "PRUEBAS Y DOCUMENTOS ANEXOS" arriba.
   Si no se especificaron pruebas, indica: "Se aportarán las pruebas pertinentes en el término legal."

   **VIII. JURAMENTO**
   "Manifiesto bajo la gravedad del juramento que no he interpuesto otra acción de tutela por los mismos hechos y derechos ante ninguna autoridad judicial."

   **IX. NOTIFICACIONES**
   Formato formal:
   "Para efectos de notificaciones:
   Dirección física: [dirección]
   Correo electrónico: [email]
   Teléfono: [teléfono]"

4. CIERRE FORMAL:
   Después de la sección IX, incluir:

   "Del señor Juez, respetuosamente,

   _________________________________
   [Nombre completo del solicitante]
   C.C. No. [número de identificación]
   Dirección: [dirección]
   Teléfono: [teléfono]
   Email: [correo electrónico]"

5. Usa lenguaje jurídico formal, profesional y técnico

6. Cita artículos constitucionales relevantes con formato correcto: "Artículo XX de la Constitución Política de Colombia" o "Art. XX C.P."

7. Las PRETENSIONES deben solicitar órdenes específicas al juez usando: "PRIMERA:", "SEGUNDA:", "TERCERA:"

8. Todos los títulos de secciones principales deben estar en NEGRITA usando formato **TÍTULO**

9. El documento debe tener apariencia de documento legal oficial, no de borrador

IMPORTANTE SOBRE JURISPRUDENCIA:
- SOLO cita jurisprudencia si estás COMPLETAMENTE SEGURO de que existe
- Si no estás seguro de una sentencia específica, NO LA CITES
- Es mejor NO citar jurisprudencia que citar sentencias inventadas
- Si citas, usa SOLO sentencias muy conocidas y emblemáticas de la Corte Constitucional
- Puedes mencionar "según jurisprudencia reiterada de la Corte Constitucional" sin número específico
- NUNCA inventes números de sentencias

El documento debe estar completo, profesional y listo para ser presentado ante un juez de la República de Colombia."""

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

HECHOS:
{datos_caso.get('hechos', '')}

CIUDAD DONDE OCURRIERON LOS HECHOS:
{datos_caso.get('ciudad_de_los_hechos', '')}

PETICIONES:
{datos_caso.get('pretensiones', '')}

FUNDAMENTOS DE DERECHO:
{datos_caso.get('fundamentos_derecho', '')}

PRUEBAS Y DOCUMENTOS ANEXOS:
{datos_caso.get('pruebas', 'No se especificaron documentos anexos')}

INSTRUCCIONES PARA FORMATO PROFESIONAL:

1. ENCABEZADO FORMAL:
   Inicia el documento con este formato exacto:

   **DERECHO DE PETICIÓN**

   Señor(a)
   REPRESENTANTE LEGAL
   {datos_caso.get('entidad_accionada', 'ENTIDAD DESTINATARIA')}
   {datos_caso.get('direccion_entidad', 'Ciudad')}

   REFERENCIA: Derecho de Petición
   PETICIONARIO: [Nombre completo del solicitante]
   ASUNTO: [Breve descripción del objeto de la petición]

   [Nombre completo del solicitante], identificado(a) como aparece al pie de mi firma, {f'actuando en calidad de {datos_caso.get("relacion_representado", "representante legal")} de {datos_caso.get("nombre_representado", "")},' if datos_caso.get('actua_en_representacion', False) else 'actuando en nombre propio,'} respetuosamente me dirijo a usted para presentar DERECHO DE PETICIÓN, con fundamento en el artículo 23 de la Constitución Política de Colombia y la Ley 1437 de 2011, con base en lo siguiente:

2. ESTRUCTURA REQUERIDA (usar NUMERACIÓN ROMANA):

   **I. OBJETO**
   Presentar la naturaleza de la petición de manera clara y directa.

   **II. HECHOS**
   Relatar los hechos cronológicamente y de forma clara.

   **III. FUNDAMENTOS DE DERECHO**
   - SIEMPRE citar el Art. 23 de la Constitución Política de Colombia
   - SIEMPRE citar la Ley 1437 de 2011 (Código de Procedimiento Administrativo y de lo Contencioso Administrativo)
   - Mencionar EXPRESAMENTE el término de respuesta:
     * 15 días hábiles (Art. 14 Ley 1437) para peticiones generales
     * 10 días hábiles (Art. 14 Ley 1437) cuando se solicitan documentos o información específica
   - Si involucra menores de edad: citar el Art. 44 C.P. (derechos fundamentales de los niños) y mencionar el interés superior del menor
   - Si involucra adultos mayores: citar el Art. 46 C.P. (protección especial a la tercera edad)
   - Si involucra personas con discapacidad: citar el Art. 47 C.P. (protección y atención especial)

   **IV. PETICIONES**
   Enumerar de forma clara, específica y accionable lo que se solicita a la entidad.
   Usar formato: "PRIMERO:", "SEGUNDO:", "TERCERO:", etc.
   Cada petición debe ser específica, medible y accionable.

   **V. ANEXOS**
   Si se especificaron pruebas o documentos anexos, USA EXACTAMENTE la información proporcionada en "PRUEBAS Y DOCUMENTOS ANEXOS" arriba.
   Formato: "- Anexo 1: [descripción]"
   Si no se especificaron, indica: "Se aportarán posteriormente los documentos necesarios."

   **VI. NOTIFICACIONES**
   Formato formal:
   "Para efectos de notificaciones y respuestas:
   Dirección física: [dirección]
   Correo electrónico: [email]
   Teléfono: [teléfono]"

3. CIERRE FORMAL:
   Después de la sección VI, incluir:

   "Cordialmente,

   _________________________________
   [Nombre completo del solicitante]
   C.C. No. [número de identificación]
   Dirección: [dirección]
   Teléfono: [teléfono]
   Email: [correo electrónico]"

4. Usa lenguaje formal, respetuoso y técnico apropiado para un derecho de petición

5. IMPORTANTE - NO uses terminología de acción de tutela:
   - NO uses: "accionante", "accionado", "juez", "sentencia", "fallo", "pretensiones", "amparo"
   - USA: "peticionario", "entidad destinataria", "respuesta", "peticiones", "solicitud"

6. Todos los títulos de secciones principales deben estar en NEGRITA usando formato **TÍTULO**

7. El documento debe tener apariencia de documento legal oficial, no de borrador

8. El documento debe estar completo y listo para radicar

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
Extrae y estructura la siguiente información en formato JSON. LEE CUIDADOSAMENTE toda la conversación y extrae los datos del caso.

IMPORTANTE - DATOS PERSONALES DEL SOLICITANTE:
Los datos personales del solicitante (nombre, identificación, dirección, teléfono, email) ya están registrados en el perfil del usuario y se auto-llenan automáticamente.

NO extraigas ni busques estos datos en la conversación. El avatar NO debe preguntar por datos personales.

Enfócate ÚNICAMENTE en extraer:
- Tipo de documento (tutela o derecho de petición)
- Datos de la entidad accionada
- Hechos del caso
- Derechos vulnerados
- Pretensiones
- Fundamentos de derecho
- Pruebas
- Si actúa en representación y datos del representado

1. **tipo_documento**: Determina el tipo de documento legal apropiado según la conversación.

   ⚖️ PRINCIPIO LEGAL CLAVE: SUBSIDIARIEDAD DE LA TUTELA (Art. 86 C.P. y Decreto 2591/1991)
   La tutela SOLO procede cuando NO existe otro medio de defensa judicial o cuando ya se agotó.
   Si no se cumple subsidiariedad, un juez rechazará la tutela de plano.

   REGLAS DE DECISIÓN ESTRICTAS (APLICAR EN ESTE ORDEN):

   ❌ DERECHO DE PETICIÓN OBLIGATORIO (subsidiariedad no cumplida):
   Si se cumplen TODAS estas condiciones:
   - NO ha presentado derecho de petición previo a la entidad
   - NO hay perjuicio irremediable (urgencia extrema que no puede esperar 15 días)
   - Es trámite administrativo normal (información, servicios, quejas, reclamos)

   → ACCIÓN: tipo_documento = "derecho_peticion"
   → razon_tipo_documento = "No procede tutela sin agotar derecho de petición previo. No hay perjuicio irremediable."

   ✅ TUTELA PROCEDE SI (subsidiariedad cumplida):

   Caso 1: YA AGOTÓ DERECHO DE PETICIÓN
   - Presentó derecho de petición hace más de 15 días Y no respondieron
   - O respondieron negando sin fundamento válido
   - O la respuesta no resolvió el problema

   → ACCIÓN: tipo_documento = "tutela"
   → razon_tipo_documento = "Procede tutela. Ya agotó derecho de petición sin solución satisfactoria."

   Caso 2: PERJUICIO IRREMEDIABLE (urgencia que no puede esperar 15 días)
   - Riesgo inminente de vida (ejemplo: necesita cirugía urgente en días)
   - Riesgo grave e inmediato para salud (ejemplo: dolor insoportable, enfermedad que avanza rápidamente)
   - Daño irreparable si se espera (ejemplo: pérdida permanente de movilidad, tratamiento de cáncer que no puede retrasarse)
   - Situación médica certificada como urgente/emergencia

   → ACCIÓN: tipo_documento = "tutela"
   → razon_tipo_documento = "Procede tutela por perjuicio irremediable. Urgencia extrema justifica excepción a subsidiariedad."

   Caso 3: NO EXISTE OTRO MECANISMO JUDICIAL
   - Se vulneran derechos fundamentales
   - NO hay otro medio de defensa judicial eficaz disponible
   - El derecho de petición NO sería suficiente para proteger el derecho

   → ACCIÓN: tipo_documento = "tutela"
   → razon_tipo_documento = "Procede tutela. No existe otro mecanismo judicial eficaz."

2. **hechos**: Narrativa cronológica y detallada de los hechos.
   Redacta en tercera persona, estilo legal.
   Si no hay información suficiente, deja este campo vacío.

3. **derechos_vulnerados**: (Solo para tutelas) Lista de derechos fundamentales vulnerados con sus artículos constitucionales.
   Formato: "Derecho a la Salud (Art. 49 C.P.), Derecho a la Vida (Art. 11 C.P.)"
   Si es derecho de petición o no hay información suficiente, deja este campo vacío.

4. **entidad_accionada**: Nombre completo de la entidad, empresa o institución.
   Debe ser el nombre oficial completo (ejemplo: "EPS Sanitas S.A.", "Ministerio de Salud").
   Si no hay información suficiente, deja este campo vacío.

5. **direccion_entidad**: La dirección de la sede de la entidad accionada.
   Busca cuando dice: "la dirección de la EPS es...", "la sede está en...", "está ubicada en...".
   Si no lo menciona, deja este campo vacío.

6. **ciudad_de_los_hechos**: La ciudad donde ocurrieron los hechos narrados.
   Busca cuando dice: "esto pasó en Bogotá", "fue en Medellín", "ocurrió en Cali", etc.
   IMPORTANTE: Solo la ciudad, no la dirección completa. Ejemplos: "Bogotá", "Medellín", "Cali".
   Si no lo menciona, deja este campo vacío.

7. **pretensiones**: Lo que solicita el usuario.
   - Para tutelas: Qué solicita que ordene el juez
   - Para derechos de petición: Qué información o actuación solicita
   Si no hay información suficiente, deja este campo vacío.

8. **fundamentos_derecho**: Leyes, decretos o jurisprudencia aplicable mencionada en la conversación.
   Solo incluye lo que fue EXPLÍCITAMENTE mencionado. Si nada fue mencionado, deja este campo vacío.

9. **pruebas**: Documentos, pruebas o anexos mencionados en la conversación.
   Incluye: diagnósticos médicos, fórmulas, fotografías, derechos de petición previos, certificaciones, etc.
   Enumera cada documento mencionado de forma clara. Si no hay información suficiente, deja este campo vacío.

10. **actua_en_representacion**: (Booleano) true si el solicitante actúa en representación de otra persona, false si actúa en nombre propio.
    Detecta frases como "mi hijo", "mi madre", "represento a", "en nombre de", etc.

11. **nombre_representado**: (Solo si actúa en representación) Nombre completo de la persona representada.
    Si no hay información suficiente, deja este campo vacío.

12. **identificacion_representado**: (Solo si actúa en representación) Documento de identidad de la persona representada.
    Si no hay información suficiente, deja este campo vacío.

13. **relacion_representado**: (Solo si actúa en representación) Relación entre el solicitante y el representado.
    Extrae EXACTAMENTE lo que dice el usuario. Ejemplos: "madre", "padre", "hermano", "hermana", "tío", "tía",
    "abuelo", "abuela", "hijo", "hija", "apoderado", "tutor legal", "cuidador", "prima", "primo", etc.
    IMPORTANTE: No limites a opciones predefinidas, acepta cualquier relación familiar o legal que mencione.
    Si no hay información suficiente, deja este campo vacío.

14. **tipo_representado**: (Solo si actúa en representación) Tipo o descripción de la persona representada.
    Extrae EXACTAMENTE lo que dice el usuario. Ejemplos: "menor de edad", "adulto mayor", "persona con discapacidad",
    "persona en condición de vulnerabilidad", "niño", "adolescente", "anciano", etc.
    IMPORTANTE: No limites a opciones predefinidas, acepta cualquier descripción que mencione el usuario.
    Si no hay información suficiente, deja este campo vacío.

15. **hubo_derecho_peticion_previo**: (Booleano) true si en la conversación se menciona que ya hubo un derecho de petición previo (presentado, radicado, enviado), false si no se menciona o no hubo.
    Esto es importante para determinar si procede directamente una tutela por subsidiariedad.

16. **detalle_derecho_peticion_previo**: (Solo si hubo derecho de petición previo) Detalles sobre el derecho de petición previo.
    Incluye: fecha de radicación, entidad a la que se dirigió, qué se solicitó, respuesta obtenida (si la hubo), razón por la que no resolvió el problema.
    Si no hay información suficiente, deja este campo vacío.

17. **tiene_perjuicio_irremediable**: (Booleano) true si existe urgencia extrema que no puede esperar 15 días, false si puede esperar.
    Evalúa si hay: riesgo de vida, riesgo grave para salud, daño irreparable, emergencia médica certificada.
    Este campo es CRÍTICO para validar si procede tutela sin derecho de petición previo.

18. **es_procedente_tutela**: (Booleano) true si la tutela cumple requisitos de subsidiariedad, false si no procede.
    Debe ser true SOLO si:
    - YA agotó derecho de petición sin solución satisfactoria
    - O tiene perjuicio irremediable (tiene_perjuicio_irremediable = true)
    - O no existe otro mecanismo judicial eficaz

19. **razon_improcedencia**: (String) Si es_procedente_tutela = false, explica brevemente por qué no procede.
    Ejemplo: "No ha agotado derecho de petición previo y no hay perjuicio irremediable"
    Si es_procedente_tutela = true, deja este campo vacío.

20. **tipo_documento_recomendado**: (String) El tipo de documento que REALMENTE debería generarse según subsidiariedad.
    Valores posibles: "tutela" o "derecho_peticion"
    - Si es_procedente_tutela = true → "tutela"
    - Si es_procedente_tutela = false → "derecho_peticion"

INSTRUCCIONES IMPORTANTES:
- ⚠️ RECUERDA: NO extraigas datos personales del solicitante (nombre, cédula, dirección, teléfono, email) - ya están en el perfil del usuario
- Lee TODA la conversación completa antes de extraer
- Si algún campo no tiene información suficiente en la conversación, devuélvelo como cadena vacía ""
- Mantén lenguaje legal apropiado para Colombia
- Redacta los hechos de forma coherente y cronológica
- Sé preciso con los artículos constitucionales (usa "Art. XX C.P.")
- NO inventes información que no esté en la conversación
- NO cites jurisprudencia a menos que haya sido mencionada explícitamente
- IMPORTANTE: Determina correctamente el tipo_documento basándote en el contexto de la conversación

FORMATO DE SALIDA:
Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta, sin markdown ni texto adicional:
{{
    "tipo_documento": "tutela" o "derecho_peticion",
    "razon_tipo_documento": "explicación breve de por qué se eligió tutela o derecho de petición",
    "hechos": "narrativa de los hechos o cadena vacía",
    "ciudad_de_los_hechos": "ciudad donde ocurrieron los hechos o cadena vacía",
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
    "detalle_derecho_peticion_previo": "detalles del derecho de petición previo o cadena vacía",
    "tiene_perjuicio_irremediable": true o false,
    "es_procedente_tutela": true o false,
    "razon_improcedencia": "razón de improcedencia o cadena vacía",
    "tipo_documento_recomendado": "tutela" o "derecho_peticion"
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
            "entidad_accionada", "direccion_entidad", "representante_legal",
            "pretensiones", "fundamentos_derecho", "pruebas",
            "actua_en_representacion", "nombre_representado", "identificacion_representado",
            "relacion_representado", "tipo_representado", "hubo_derecho_peticion_previo",
            "detalle_derecho_peticion_previo", "tiene_perjuicio_irremediable",
            "es_procedente_tutela", "razon_improcedencia", "tipo_documento_recomendado"
        ]
        for campo in campos_esperados:
            if campo not in datos_extraidos:
                if campo == "tipo_documento":
                    datos_extraidos[campo] = "tutela"  # Valor por defecto
                elif campo in ["actua_en_representacion", "hubo_derecho_peticion_previo",
                               "tiene_perjuicio_irremediable", "es_procedente_tutela"]:
                    datos_extraidos[campo] = False  # Valor por defecto para booleanos
                elif campo == "tipo_documento_recomendado":
                    datos_extraidos[campo] = "derecho_peticion"  # Por defecto recomendar derecho de petición (subsidiariedad)
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
