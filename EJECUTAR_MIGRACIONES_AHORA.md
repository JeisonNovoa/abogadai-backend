# 🚀 CÓMO EJECUTAR LAS MIGRACIONES AHORA

## ✅ Situación Actual

- ✅ Los cambios ya fueron commited y pusheados a GitHub
- ✅ El backend está desplegado y funcionando en Render
- ⏳ El nuevo endpoint de migraciones se está desplegando
- ⚠️ La conexión directa desde tu máquina local está bloqueada por firewall

## 🎯 OPCIÓN 1: Esperar y Usar el Endpoint API (RECOMENDADO - MÁS FÁCIL)

### Paso 1: Esperar a que Render complete el deployment (2-10 minutos)

Render detecta automáticamente los cambios en GitHub y redespliega.
Esto puede tardar entre 2 y 10 minutos.

### Paso 2: Verificar si el endpoint está listo

Abre tu navegador o terminal y ejecuta:

```bash
curl https://abogadai-backend.onrender.com/api/migrations/status
```

Si ves un JSON con información sobre las migraciones, el endpoint está listo.
Si ves `{"detail":"Not Found"}`, espera un poco más.

### Paso 3: Ejecutar las migraciones

Una vez que el endpoint esté disponible, ejecuta:

```bash
cd abogadai-backend
./venv/Scripts/python.exe execute_migrations_production.py
```

O usando curl directamente:

```bash
curl -X POST https://abogadai-backend.onrender.com/api/migrations/apply \
  -H "X-Migration-Secret: tu-secret-key-super-segura-cambiala-en-produccion" \
  -H "Content-Type: application/json"
```

**IMPORTANTE**: Reemplaza `tu-secret-key-super-segura-cambiala-en-produccion` con la SECRET_KEY real de tu .env de producción en Render.

---

## 🎯 OPCIÓN 2: Ejecutar Manualmente desde Render (FUNCIONA INMEDIATAMENTE)

Si no quieres esperar al deployment, puedes ejecutar las migraciones directamente desde Render:

### Paso 1: Acceder al Shell de PostgreSQL en Render

1. Ve a https://dashboard.render.com/
2. Inicia sesión con tu cuenta
3. Selecciona tu base de datos PostgreSQL: **abogadai_db**
4. En el menú lateral, haz clic en **"Shell"** o **"Connect"**

### Paso 2: Copiar y Ejecutar el SQL

1. Abre el archivo `MIGRATION_SQL_FOR_PRODUCTION.sql` en este directorio
2. Copia **TODO** el contenido del archivo
3. Pégalo en el shell de PostgreSQL de Render
4. Presiona **Enter** para ejecutar

### Paso 3: Verificar

Deberías ver mensajes como:
```
NOTICE: Campo ciudad_de_los_hechos agregado exitosamente
NOTICE: Campo representante_legal eliminado exitosamente
NOTICE: Campo documento_desbloqueado agregado exitosamente
NOTICE: Campo fecha_pago agregado exitosamente
```

Y al final, una tabla mostrando todas las columnas de la tabla `casos`.

✅ **¡LISTO!** Las migraciones están aplicadas.

---

## 🎯 OPCIÓN 3: Forzar Redeploy en Render

Si el deployment está atascado:

1. Ve a https://dashboard.render.com/
2. Selecciona tu servicio web (backend)
3. Haz clic en "Manual Deploy" → "Deploy latest commit"

Espera 2-5 minutos y luego usa la OPCIÓN 1.

---

## 📋 Verificar que las Migraciones se Aplicaron

Después de ejecutar las migraciones (por cualquier método), verifica:

```bash
curl https://abogadai-backend.onrender.com/api/migrations/status
```

Deberías ver:
```json
{
  "all_migrations_applied": true,
  "required_columns": {
    "ciudad_de_los_hechos": true,
    "documento_desbloqueado": true,
    "fecha_pago": true
  },
  "columns_that_should_not_exist": {
    "representante_legal": false
  },
  ...
}
```

---

## ⚠️ Resumen de Cambios Aplicados

Una vez completadas las migraciones, tu base de datos tendrá:

✅ **Nuevos campos agregados:**
- `ciudad_de_los_hechos` (VARCHAR 100) - para guardar la ciudad donde ocurrieron los hechos
- `documento_desbloqueado` (BOOLEAN DEFAULT FALSE) - para el sistema de paywall
- `fecha_pago` (TIMESTAMP) - para registrar cuándo se desbloqueó el documento

✅ **Campos eliminados:**
- `representante_legal` - ya no es necesario

**NOTA**: Todos los documentos existentes tendrán `documento_desbloqueado = FALSE` por defecto.

---

## 🆘 Problemas?

Si tienes algún problema:

1. **El endpoint no está disponible después de 10 minutos**:
   - Revisa los logs de deployment en Render
   - Usa la OPCIÓN 2 (manual)

2. **Error al ejecutar SQL en Render**:
   - Verifica que copiaste TODO el contenido del archivo SQL
   - El script es seguro y verifica si los cambios ya existen antes de aplicarlos

3. **La SECRET_KEY no funciona**:
   - Verifica las variables de entorno en Render
   - Usa la SECRET_KEY configurada en el dashboard de Render

---

## 📝 Archivos de Referencia

- `MIGRATION_SQL_FOR_PRODUCTION.sql` - Script SQL para ejecutar manualmente
- `execute_migrations_production.py` - Script Python para ejecutar vía API
- `apply_migrations_direct.py` - Script de conexión directa (no funciona desde local)
