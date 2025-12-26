"""
Script que espera a que el endpoint esté disponible y ejecuta las migraciones automáticamente
"""

import requests
import time
import json
import sys

BACKEND_URL = "https://abogadai-backend.onrender.com"
SECRET_KEY = "tu-secret-key-super-segura-cambiala-en-produccion"  # Actualiza con la SECRET_KEY de producción
MAX_WAIT_MINUTES = 15
CHECK_INTERVAL_SECONDS = 30

def check_endpoint_available():
    """Verifica si el endpoint de migraciones está disponible"""
    try:
        url = f"{BACKEND_URL}/api/migrations/status"
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_migration_status():
    """Obtiene el estado de las migraciones"""
    try:
        url = f"{BACKEND_URL}/api/migrations/status"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error obteniendo estado: {str(e)}")
        return None

def apply_migrations():
    """Aplica las migraciones"""
    try:
        url = f"{BACKEND_URL}/api/migrations/apply"
        headers = {
            "X-Migration-Secret": SECRET_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, timeout=60)

        if response.status_code == 403:
            print("")
            print("=" * 70)
            print("ERROR: Clave de migracion invalida")
            print("=" * 70)
            print("")
            print("Actualiza la SECRET_KEY en este script (linea 11) con la clave de produccion")
            print("La clave debe coincidir con la variable de entorno SECRET_KEY en Render")
            print("")
            return None

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"Error aplicando migraciones: {str(e)}")
        return None

def main():
    print("")
    print("=" * 70)
    print("SCRIPT AUTOMATICO DE MIGRACIONES")
    print("=" * 70)
    print("")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Tiempo maximo de espera: {MAX_WAIT_MINUTES} minutos")
    print(f"Intervalo de verificacion: {CHECK_INTERVAL_SECONDS} segundos")
    print("")

    # Paso 1: Esperar a que el endpoint esté disponible
    print("PASO 1: Esperando a que el endpoint de migraciones este disponible...")
    print("")

    start_time = time.time()
    attempts = 0

    while True:
        attempts += 1
        elapsed_minutes = (time.time() - start_time) / 60

        if elapsed_minutes > MAX_WAIT_MINUTES:
            print("")
            print("=" * 70)
            print("TIMEOUT: El endpoint no estuvo disponible despues de 15 minutos")
            print("=" * 70)
            print("")
            print("OPCIONES:")
            print("  1. Verifica el estado del deployment en Render")
            print("  2. Ejecuta las migraciones manualmente desde el shell de Render")
            print("  3. Ve el archivo EJECUTAR_MIGRACIONES_AHORA.md para instrucciones")
            print("")
            sys.exit(1)

        print(f"Intento {attempts} - Verificando endpoint... ", end="")

        if check_endpoint_available():
            print("OK - Endpoint disponible!")
            break
        else:
            print(f"No disponible aun. Esperando {CHECK_INTERVAL_SECONDS} segundos...")
            time.sleep(CHECK_INTERVAL_SECONDS)

    print("")
    print("=" * 70)
    print("ENDPOINT DISPONIBLE")
    print("=" * 70)
    print("")

    # Paso 2: Verificar estado actual
    print("PASO 2: Verificando estado actual de migraciones...")
    print("")

    status = get_migration_status()
    if status:
        print("Estado actual:")
        print(json.dumps(status, indent=2))
        print("")

        if status.get("all_migrations_applied"):
            print("=" * 70)
            print("TODAS LAS MIGRACIONES YA ESTAN APLICADAS")
            print("=" * 70)
            print("")
            print("No es necesario hacer nada mas.")
            print("")
            sys.exit(0)

    # Paso 3: Aplicar migraciones
    print("PASO 3: Aplicando migraciones...")
    print("")

    result = apply_migrations()
    if not result:
        print("")
        print("Error al aplicar migraciones. Revisa los mensajes anteriores.")
        sys.exit(1)

    print("")
    print("Resultado:")
    print(json.dumps(result, indent=2))
    print("")

    if result.get("success"):
        print("=" * 70)
        print("MIGRACIONES APLICADAS EXITOSAMENTE")
        print("=" * 70)
        print("")
        if result.get("migrations_applied"):
            print("Migraciones aplicadas:")
            for migration in result["migrations_applied"]:
                print(f"  - {migration}")
        if result.get("migrations_skipped"):
            print("")
            print("Migraciones omitidas (ya existian):")
            for migration in result["migrations_skipped"]:
                print(f"  - {migration}")
        print("")

        # Verificación final
        print("PASO 4: Verificacion final...")
        print("")
        final_status = get_migration_status()
        if final_status and final_status.get("all_migrations_applied"):
            print("=" * 70)
            print("PROCESO COMPLETADO EXITOSAMENTE")
            print("=" * 70)
            print("")
            print("Las migraciones se aplicaron correctamente a la base de datos de produccion.")
            print("")
        else:
            print("ADVERTENCIA: Algunas migraciones pueden no haberse aplicado correctamente.")
    else:
        print("=" * 70)
        print("ERROR AL APLICAR MIGRACIONES")
        print("=" * 70)
        if result.get("errors"):
            for error in result["errors"]:
                print(f"  - {error}")
        print("")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("")
        print("")
        print("Operacion cancelada por el usuario.")
        print("")
        sys.exit(0)
