# -*- coding: utf-8 -*-
"""
Script de migración para agregar el valor 'abandonado' al enum EstadoCaso
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

print("Migración: Agregar estado 'abandonado' al enum EstadoCaso")
print("=" * 60)

# Determinar si usamos DATABASE_URL (producción) o credenciales locales
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    print("[INFO] Usando DATABASE_URL de variable de entorno (PRODUCCIÓN)")
    DB_CONFIG = DATABASE_URL
else:
    print("[INFO] Usando credenciales locales (DESARROLLO)")
    DB_CONFIG = {
        "host": "localhost",
        "port": "5432",
        "database": "abogadai_db",
        "user": "abogadai_user",
        "password": "abogadai123"
    }

try:
    print("[1/4] Conectando a la base de datos...")
    if isinstance(DB_CONFIG, str):
        # DATABASE_URL format
        conn = psycopg2.connect(DB_CONFIG)
    else:
        # Dict format
        conn = psycopg2.connect(**DB_CONFIG)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    print("[OK] Conectado")

    print("[2/4] Verificando enum 'estadocaso'...")
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type
            WHERE typname = 'estadocaso'
        );
    """)
    enum_existe = cur.fetchone()[0]

    if not enum_existe:
        print("[ERROR] El enum 'estadocaso' no existe")
        sys.exit(1)

    print("[OK] Enum encontrado")

    print("[3/4] Verificando valores actuales del enum...")
    cur.execute("""
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'estadocaso'
        ORDER BY e.enumsortorder;
    """)
    valores_actuales = [row[0] for row in cur.fetchall()]

    print(f"  Valores actuales: {', '.join(valores_actuales)}")

    if 'abandonado' in valores_actuales:
        print("[OK] El valor 'abandonado' ya existe en el enum")
        cur.close()
        conn.close()
        sys.exit(0)

    print("[4/4] Agregando valor 'abandonado' al enum...")
    try:
        cur.execute("ALTER TYPE estadocaso ADD VALUE 'abandonado';")
        print("  [OK] Valor 'abandonado' agregado exitosamente")
    except Exception as e:
        print(f"  [ERROR] No se pudo agregar el valor: {e}")
        raise

    print("\n[5/5] Verificando resultado final...")
    cur.execute("""
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'estadocaso'
        ORDER BY e.enumsortorder;
    """)
    valores_finales = [row[0] for row in cur.fetchall()]

    print("\nValores finales del enum 'estadocaso':")
    for i, valor in enumerate(valores_finales, 1):
        print(f"  {i}. {valor}")

    cur.close()
    conn.close()

    print("\n✅ [OK] MIGRACIÓN COMPLETADA")

except Exception as e:
    print(f"\n❌ [ERROR] {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
