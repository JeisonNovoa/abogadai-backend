# Instrucciones para Aplicar Migraciones a Producción

## Resumen de Cambios

Se necesitan aplicar las siguientes migraciones a la base de datos de producción:

### Migración 1 (17-dic-2025): Actualizar campos de caso
- ✅ Agregar campo `ciudad_de_los_hechos` (VARCHAR 100)
- ✅ Eliminar campo `representante_legal`

### Migración 2 (19-dic-2025): Sistema de paywall
- ✅ Agregar campo `documento_desbloqueado` (BOOLEAN DEFAULT FALSE NOT NULL)
- ✅ Agregar campo `fecha_pago` (TIMESTAMP)

---

## Opción 1: Aplicar desde el Panel de Render (RECOMENDADO)

### Paso 1: Acceder al Shell de la Base de Datos

1. Ve a https://dashboard.render.com/
2. Selecciona tu servicio de PostgreSQL: `abogadai_db`
3. Haz clic en la pestaña "Shell" en el menú superior

### Paso 2: Ejecutar el Script

1. Abre el archivo `MIGRATION_SQL_FOR_PRODUCTION.sql`
2. Copia TODO el contenido del archivo
3. Pégalo en el shell de Render
4. Presiona Enter para ejecutar

### Paso 3: Verificar

Deberías ver mensajes como:
```
NOTICE: Campo ciudad_de_los_hechos agregado exitosamente
NOTICE: Campo representante_legal eliminado exitosamente
NOTICE: Campo documento_desbloqueado agregado exitosamente
NOTICE: Campo fecha_pago agregado exitosamente
```

Y al final, una tabla mostrando todas las columnas de la tabla `casos`.

---

## Opción 2: Usar psql desde la Línea de Comandos

Si tienes `psql` instalado en tu sistema:

```bash
psql postgresql://abogadai_db_user:zz2U57KjeZbinZqNAwIr2SICUnU68Ezj@dpg-d4stu1chg0os73csqgqg-a.virginia-postgres.render.com/abogadai_db -f MIGRATION_SQL_FOR_PRODUCTION.sql
```

O usando la variable de entorno:

```bash
set PGPASSWORD=zz2U57KjeZbinZqNAwIr2SICUnU68Ezj
psql -h dpg-d4stu1chg0os73csqgqg-a.virginia-postgres.render.com -U abogadai_db_user -d abogadai_db -f MIGRATION_SQL_FOR_PRODUCTION.sql
```

---

## Opción 3: Habilitar Acceso Externo en Render

Si prefieres ejecutar el script Python desde tu máquina local:

### Paso 1: Verificar Configuración de Red en Render

1. Ve a tu dashboard de Render
2. Selecciona la base de datos
3. En la pestaña "Settings" o "Access Control"
4. Asegúrate de que "External Access" esté habilitado
5. Si hay una lista de IPs permitidas, agrega tu IP actual

### Paso 2: Ejecutar el Script Python

```bash
cd abogadai-backend
./venv/Scripts/python.exe apply_migrations_to_production.py --confirm
```

---

## Verificación Post-Migración

Una vez aplicadas las migraciones, verifica que los cambios se aplicaron correctamente ejecutando:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'casos'
ORDER BY ordinal_position;
```

Deberías ver los nuevos campos:
- `ciudad_de_los_hechos` (VARCHAR)
- `documento_desbloqueado` (BOOLEAN)
- `fecha_pago` (TIMESTAMP)

Y NO deberías ver:
- `representante_legal`

---

## Notas Importantes

- ⚠️ Todos los casos existentes tendrán `documento_desbloqueado = FALSE` por defecto
- ⚠️ Los usuarios necesitarán "pagar" para desbloquear cada documento
- ⚠️ La descarga de PDF estará bloqueada hasta el desbloqueo
- ⚠️ La descarga de DOCX permanece sin restricciones

---

## Archivos Relacionados

- `MIGRATION_SQL_FOR_PRODUCTION.sql` - Script SQL para ejecutar en Render
- `apply_migrations_to_production.py` - Script Python alternativo
- `migrate_update_ciudad_representante.py` - Migración original (17-dic)
- `migrate_add_paywall_fields.py` - Migración original (19-dic)

---

## Soporte

Si tienes problemas con la migración:
1. Verifica que estés conectado a la base de datos correcta
2. Verifica que tengas permisos de escritura en la base de datos
3. Revisa los logs de error en el shell de Render
4. Los scripts están diseñados para ser seguros y no duplicar cambios si ya existen
