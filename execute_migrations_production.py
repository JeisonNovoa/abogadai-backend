"""
Script para ejecutar migraciones en producción mediante el endpoint API
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuración
BACKEND_URL = "https://abogadai-backend.onrender.com"  # Actualiza si es diferente
SECRET_KEY = "tu-secret-key-super-segura-cambiala-en-produccion"  # Actualiza con la SECRET_KEY de producción

def check_migration_status() -> Dict[str, Any]:
    """Verifica el estado de las migraciones sin aplicarlas"""
    print("=" * 70)
    print("VERIFICANDO ESTADO DE MIGRACIONES")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print("")

    try:
        url = f"{BACKEND_URL}/api/migrations/status"
        print(f"GET {url}")

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        print("")
        print("ESTADO ACTUAL:")
        print(json.dumps(data, indent=2))
        print("")

        return data

    except requests.exceptions.ConnectionError:
        print("ERROR: No se pudo conectar al backend.")
        print("Verifica que:")
        print("  1. El backend esté desplegado en Render")
        print("  2. La URL del backend sea correcta")
        print("  3. El deployment haya terminado")
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


def apply_migrations() -> Dict[str, Any]:
    """Aplica las migraciones a la base de datos de producción"""
    print("=" * 70)
    print("APLICANDO MIGRACIONES A PRODUCCIÓN")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print("")

    try:
        url = f"{BACKEND_URL}/api/migrations/apply"
        headers = {
            "X-Migration-Secret": SECRET_KEY,
            "Content-Type": "application/json"
        }

        print(f"POST {url}")
        print("Headers: X-Migration-Secret: [REDACTED]")
        print("")

        response = requests.post(url, headers=headers, timeout=60)

        if response.status_code == 403:
            print("ERROR: Clave de migración inválida")
            print("Actualiza la SECRET_KEY en este script con la clave de producción")
            sys.exit(1)

        response.raise_for_status()

        data = response.json()
        print("")
        print("RESULTADO:")
        print(json.dumps(data, indent=2))
        print("")

        if data.get("success"):
            print("=" * 70)
            print("✓ MIGRACIONES APLICADAS EXITOSAMENTE")
            print("=" * 70)
            print("")
            print("Migraciones aplicadas:")
            for migration in data.get("migrations_applied", []):
                print(f"  ✓ {migration}")
            print("")
            if data.get("migrations_skipped"):
                print("Migraciones omitidas (ya existían):")
                for migration in data.get("migrations_skipped", []):
                    print(f"  ○ {migration}")
                print("")
        else:
            print("=" * 70)
            print("✗ ERROR AL APLICAR MIGRACIONES")
            print("=" * 70)
            if data.get("errors"):
                for error in data["errors"]:
                    print(f"  • {error}")

        return data

    except requests.exceptions.ConnectionError:
        print("ERROR: No se pudo conectar al backend.")
        print("Verifica que:")
        print("  1. El backend esté desplegado en Render")
        print("  2. La URL del backend sea correcta")
        print("  3. El deployment haya terminado")
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    print("")
    print("SCRIPT DE MIGRACIONES PARA PRODUCCIÓN")
    print("=" * 70)
    print("")
    print("Este script hará lo siguiente:")
    print("  1. Verificar el estado actual de las migraciones")
    print("  2. Aplicar las migraciones pendientes")
    print("  3. Verificar que se aplicaron correctamente")
    print("")

    # Paso 1: Verificar estado actual
    print("PASO 1: Verificando estado actual...")
    print("")
    status_before = check_migration_status()

    if status_before.get("all_migrations_applied"):
        print("=" * 70)
        print("TODAS LAS MIGRACIONES YA ESTÁN APLICADAS")
        print("=" * 70)
        print("No es necesario hacer nada.")
        sys.exit(0)

    # Paso 2: Confirmar ejecución
    print("")
    print("ADVERTENCIA: Estás a punto de aplicar migraciones a PRODUCCIÓN")
    print("")
    response = input("¿Continuar? (yes/no): ")

    if response.lower() not in ['yes', 'y', 'si', 's']:
        print("Operación cancelada.")
        sys.exit(0)

    print("")

    # Paso 3: Aplicar migraciones
    print("PASO 2: Aplicando migraciones...")
    print("")
    result = apply_migrations()

    # Paso 4: Verificar estado final
    print("")
    print("PASO 3: Verificando estado final...")
    print("")
    status_after = check_migration_status()

    if status_after.get("all_migrations_applied"):
        print("=" * 70)
        print("✓ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        print("")
        print("Las migraciones se aplicaron correctamente a la base de datos de producción.")
    else:
        print("=" * 70)
        print("⚠ ADVERTENCIA")
        print("=" * 70)
        print("Algunas migraciones pueden no haberse aplicado correctamente.")
        print("Revisa los logs anteriores para más detalles.")
