# -*- coding: utf-8 -*-
"""
Migración: Sistema de Niveles y Reembolsos
Versión simplificada para Windows
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models import User, Caso, Pago
from sqlalchemy import text

def migrate():
    print("="*60)
    print("MIGRACION: Sistema de Niveles y Reembolsos")
    print("="*60)

    db = SessionLocal()

    try:
        # 1. Agregar columnas a users
        print("\nPaso 1: Agregando columnas a tabla 'users'...")

        columnas_users = [
            "ALTER TABLE users ADD COLUMN nivel_usuario INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN pagos_ultimo_mes INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN ultimo_recalculo_nivel TIMESTAMP",
            "ALTER TABLE users ADD COLUMN sesiones_extra_hoy INTEGER DEFAULT 0"
        ]

        for sql in columnas_users:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"  OK: {sql[:40]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  SKIP: Columna ya existe")
                    db.rollback()
                else:
                    print(f"  ERROR: {str(e)[:50]}")
                    db.rollback()

        # 2. Agregar columnas a casos
        print("\nPaso 2: Agregando columnas a tabla 'casos'...")

        columnas_casos = [
            "ALTER TABLE casos ADD COLUMN fecha_vencimiento TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN reembolso_solicitado INTEGER DEFAULT 0",
            "ALTER TABLE casos ADD COLUMN fecha_solicitud_reembolso TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN motivo_rechazo TEXT",
            "ALTER TABLE casos ADD COLUMN evidencia_rechazo_url VARCHAR(500)",
            "ALTER TABLE casos ADD COLUMN fecha_reembolso TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN comentario_admin_reembolso TEXT"
        ]

        for sql in columnas_casos:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"  OK: {sql[:40]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  SKIP: Columna ya existe")
                    db.rollback()
                else:
                    print(f"  ERROR: {str(e)[:50]}")
                    db.rollback()

        # 3. Crear tabla sesiones_diarias
        print("\nPaso 3: Creando tabla 'sesiones_diarias'...")

        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS sesiones_diarias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    fecha DATE NOT NULL,
                    sesiones_creadas INTEGER DEFAULT 0,
                    minutos_consumidos INTEGER DEFAULT 0,
                    sesiones_base_permitidas INTEGER NOT NULL,
                    sesiones_extra_bonus INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            db.commit()
            print("  OK: Tabla creada")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  SKIP: Tabla ya existe")
                db.rollback()
            else:
                print(f"  ERROR: {str(e)[:50]}")
                db.rollback()

        # Indices
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_sesiones_user ON sesiones_diarias(user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_sesiones_fecha ON sesiones_diarias(fecha)"))
            db.commit()
            print("  OK: Indices creados")
        except:
            db.rollback()

        # 4. Crear enums para PostgreSQL
        print("\nPaso 4a: Creando enums (PostgreSQL)...")

        try:
            db.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE estadopago AS ENUM ('pendiente', 'exitoso', 'fallido', 'reembolsado');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            db.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE metodopago AS ENUM ('simulado', 'mercadopago', 'wompi', 'pse', 'tarjeta');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            db.commit()
            print("  OK: Enums creados")
        except Exception as e:
            print(f"  SKIP: {str(e)[:40]} (SQLite?)")
            db.rollback()

        # 4b. Crear tabla pagos
        print("\nPaso 4b: Creando tabla 'pagos'...")

        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS pagos (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    caso_id INTEGER NOT NULL,
                    monto NUMERIC(10, 2) NOT NULL,
                    estado VARCHAR(50) DEFAULT 'exitoso',
                    metodo_pago VARCHAR(50) DEFAULT 'simulado',
                    referencia_pago VARCHAR(200),
                    referencia_reembolso VARCHAR(200),
                    fecha_pago TIMESTAMP,
                    fecha_reembolso TIMESTAMP,
                    motivo_reembolso TEXT,
                    notas_admin TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (caso_id) REFERENCES casos(id) ON DELETE CASCADE
                )
            """))
            db.commit()
            print("  OK: Tabla creada")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  SKIP: Tabla ya existe")
                db.rollback()
            else:
                print(f"  ERROR: {str(e)[:50]}")
                db.rollback()

        # Indices
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_user ON pagos(user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_caso ON pagos(caso_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado)"))
            db.commit()
            print("  OK: Indices creados")
        except:
            db.rollback()

        # 5. Migrar datos existentes
        print("\nPaso 5: Migrando datos existentes...")

        # Casos pagados -> crear registros de pago (SQL directo)
        print(f"  Migrando casos pagados a tabla pagos...")

        db.execute(text("""
            INSERT INTO pagos (user_id, caso_id, monto, estado, metodo_pago, fecha_pago, created_at, updated_at)
            SELECT
                user_id,
                id as caso_id,
                50000 as monto,
                'exitoso' as estado,
                'simulado' as metodo_pago,
                fecha_pago,
                fecha_pago as created_at,
                fecha_pago as updated_at
            FROM casos
            WHERE documento_desbloqueado = TRUE
            AND fecha_pago IS NOT NULL
            AND id NOT IN (SELECT caso_id FROM pagos)
        """))
        db.commit()

        # Contar cuantos se migraron
        count = db.execute(text("SELECT COUNT(*) FROM pagos")).scalar()
        print(f"  OK: {count} pagos en total")

        # Actualizar estados
        db.execute(text("""
            UPDATE casos
            SET estado = 'pagado'
            WHERE documento_desbloqueado = TRUE
            AND estado != 'pagado'
        """))
        db.commit()
        print("  OK: Estados actualizados")

        # Fechas de vencimiento
        db.execute(text("""
            UPDATE casos
            SET fecha_vencimiento = created_at + INTERVAL '14 days'
            WHERE estado = 'GENERADO'
            AND documento_desbloqueado = FALSE
            AND fecha_vencimiento IS NULL
        """))
        db.commit()
        print("  OK: Fechas de vencimiento actualizadas")

        # 6. Recalcular niveles
        print("\nPaso 6: Recalculando niveles de usuarios...")

        usuarios = db.query(User).all()
        hace_30_dias = datetime.utcnow() - timedelta(days=30)

        for usuario in usuarios:
            pagos_mes = db.query(Pago).filter(
                Pago.user_id == usuario.id,
                Pago.estado == "exitoso",  # String en lugar de enum
                Pago.fecha_pago >= hace_30_dias
            ).count()

            if pagos_mes == 0:
                nivel = 0
            elif pagos_mes == 1:
                nivel = 1
            elif pagos_mes == 2:
                nivel = 2
            else:
                nivel = 3

            usuario.pagos_ultimo_mes = pagos_mes
            usuario.nivel_usuario = nivel
            usuario.ultimo_recalculo_nivel = datetime.utcnow()

        db.commit()
        print(f"  OK: {len(usuarios)} usuarios actualizados")

        # Distribución
        niveles = {0: 0, 1: 0, 2: 0, 3: 0}
        for u in usuarios:
            niveles[u.nivel_usuario] += 1

        print("\nDistribucion de niveles:")
        print(f"  FREE:   {niveles[0]} usuarios")
        print(f"  BRONCE: {niveles[1]} usuarios")
        print(f"  PLATA:  {niveles[2]} usuarios")
        print(f"  ORO:    {niveles[3]} usuarios")

        print("\n" + "="*60)
        print("MIGRACION COMPLETADA")
        print("="*60)

        return True

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SISTEMA DE NIVELES Y REEMBOLSOS - MIGRACION")
    print("="*60)
    print("\nEsta migracion agregara:")
    print("- Campos de niveles a users")
    print("- Campos de reembolsos a casos")
    print("- Tabla sesiones_diarias")
    print("- Tabla pagos")

    input("\nPresiona ENTER para continuar...")

    success = migrate()
    sys.exit(0 if success else 1)
