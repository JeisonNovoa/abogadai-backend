# Configuración de Tareas CRON - AbogadAI

Este documento explica cómo configurar las tareas programadas (CRON jobs) para el sistema.

## 📋 Tareas Disponibles

### 1. `tarea_medianoche` (00:00 diario)
Ejecuta mantenimiento nocturno del sistema:
- ✅ Recalcula niveles de todos los usuarios basado en pagos del último mes
- ✅ Resetea sesiones_extra_hoy a 0 para todos los usuarios
- ✅ Elimina registros de sesiones_diarias mayores a 90 días

### 2. `tarea_limpieza` (01:00 diario)
Limpia datos obsoletos:
- ✅ Elimina documentos GENERADOS vencidos (14+ días sin pagar)
- ✅ Elimina casos TEMPORAL abandonados (1+ día sin completar)

### 3. `tarea_completa` (manual)
Ejecuta todas las tareas en orden. Útil para:
- Testing
- Mantenimiento manual
- Primera configuración

## 🚀 Ejecución Manual

### Desde la línea de comandos:

```bash
cd /path/to/abogadai-backend

# Activar entorno virtual (si aplica)
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Ejecutar tarea específica
python -m app.cron.tareas_diarias medianoche
python -m app.cron.tareas_diarias limpieza
python -m app.cron.tareas_diarias completa
```

### Desde Windows PowerShell:

```powershell
cd "C:\path\to\abogadai-backend"
.\venv\Scripts\python.exe -m app.cron.tareas_diarias medianoche
```

## ⏰ Configuración CRON (Linux/Mac)

### 1. Editar crontab:

```bash
crontab -e
```

### 2. Agregar las siguientes líneas:

```bash
# AbogadAI - Tareas programadas
# Asegúrate de usar la ruta absoluta correcta

# Tarea medianoche (00:00 diario)
0 0 * * * cd /path/to/abogadai-backend && /path/to/venv/bin/python -m app.cron.tareas_diarias medianoche >> /var/log/abogadai/cron_medianoche.log 2>&1

# Tarea limpieza (01:00 diario)
0 1 * * * cd /path/to/abogadai-backend && /path/to/venv/bin/python -m app.cron.tareas_diarias limpieza >> /var/log/abogadai/cron_limpieza.log 2>&1
```

### 3. Crear directorio de logs:

```bash
sudo mkdir -p /var/log/abogadai
sudo chown $USER:$USER /var/log/abogadai
```

### 4. Verificar que se agregaron:

```bash
crontab -l
```

## 🪟 Configuración en Windows (Task Scheduler)

### Opción 1: PowerShell Script

1. Crear archivo `cron_medianoche.ps1`:

```powershell
cd "C:\path\to\abogadai-backend"
& ".\venv\Scripts\python.exe" -m app.cron.tareas_diarias medianoche
```

2. Abrir **Task Scheduler**
3. Crear tarea nueva:
   - Trigger: Diario a las 00:00
   - Action: Ejecutar script PowerShell
   - Program: `powershell.exe`
   - Arguments: `-File "C:\path\to\cron_medianoche.ps1"`

### Opción 2: Batch Script

1. Crear archivo `cron_medianoche.bat`:

```batch
@echo off
cd /d "C:\path\to\abogadai-backend"
.\venv\Scripts\python.exe -m app.cron.tareas_diarias medianoche
```

2. Configurar en Task Scheduler igual que arriba

## 📊 Monitoreo

### Ver logs en tiempo real (Linux):

```bash
tail -f /var/log/abogadai/cron_medianoche.log
tail -f /var/log/abogadai/cron_limpieza.log
```

### Verificar última ejecución:

```bash
grep "COMPLETADA" /var/log/abogadai/cron_medianoche.log | tail -n 1
```

## 🧪 Testing

### Probar tarea antes de configurar cron:

```bash
# Ejecutar manualmente y ver output
python -m app.cron.tareas_diarias medianoche

# Verificar código de salida
echo $?  # 0 = éxito, 1 = error
```

### Ejecutar todas las tareas (testing completo):

```bash
python -m app.cron.tareas_diarias completa
```

## 📝 Notas Importantes

1. **Rutas absolutas**: Siempre usa rutas absolutas en crontab
2. **Entorno virtual**: Asegúrate de activar el venv o usar la ruta completa al python del venv
3. **Permisos**: El usuario que ejecuta cron debe tener permisos de escritura en la BD
4. **Logs**: Mantén logs para debugging (usa `>>` para append)
5. **Timezone**: Cron usa el timezone del sistema, verifica con `date`

## 🔧 Troubleshooting

### Cron no se ejecuta:

```bash
# Verificar que cron está corriendo
sudo systemctl status cron  # Linux
sudo service cron status    # Alternative

# Ver logs del sistema de cron
sudo tail -f /var/log/syslog | grep CRON
```

### Errores de permisos:

```bash
# Dar permisos de ejecución al script
chmod +x /path/to/venv/bin/python
```

### Variables de entorno:

Si usas variables de entorno (.env), agrega al inicio del crontab:

```bash
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
```

## 📅 Horarios Recomendados

- **00:00** - `tarea_medianoche`: Poco tráfico, ideal para recálculos
- **01:00** - `tarea_limpieza`: Después de medianoche para evitar conflictos

**IMPORTANTE**: Ajusta los horarios según el timezone de tus usuarios principales.
