"""
Migracin: Sistema de Niveles, Lmites de Sesiones y Reembolsos
Fecha: 2025-12-22

Agrega:
- Campos de niveles y lmites a tabla users
- Campos de reembolsos a tabla casos
- Nuevas tablas: sesiones_diarias, pagos
- Actualiza enum EstadoCaso con nuevos estados
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio raz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, SessionLocal
from app.models import User, Caso, SesionDiaria, Pago, EstadoCaso, EstadoPago
from sqlalchemy import text

def migrate():
    """Ejecuta la migracin"""
    print("Iniciando migracion: Sistema de Niveles y Reembolsos")
    print("=" * 60)

    db = SessionLocal()

    try:
        # 1. AGREGAR COLUMNAS A TABLA USERS
        print("\nä Paso 1: Agregando columnas a tabla 'users'...")

        columnas_users = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS nivel_usuario INTEGER DEFAULT 0 NOT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS pagos_ultimo_mes INTEGER DEFAULT 0 NOT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ultimo_recalculo_nivel TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sesiones_extra_hoy INTEGER DEFAULT 0 NOT NULL"
        ]

        for sql in columnas_users:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"    {sql[:50]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"     Columna ya existe, omitiendo...")
                    db.rollback()
                else:
                    raise

        # 2. AGREGAR COLUMNAS A TABLA CASOS
        print("\nä Paso 2: Agregando columnas a tabla 'casos'...")

        columnas_casos = [
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS fecha_vencimiento TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS reembolso_solicitado BOOLEAN DEFAULT FALSE NOT NULL",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS fecha_solicitud_reembolso TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS evidencia_rechazo_url VARCHAR(500)",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS fecha_reembolso TIMESTAMP",
            "ALTER TABLE casos ADD COLUMN IF NOT EXISTS comentario_admin_reembolso TEXT"
        ]

        for sql in columnas_casos:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"    {sql[:50]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"     Columna ya existe, omitiendo...")
                    db.rollback()
                else:
                    raise

        # 3. ACTUALIZAR ENUM DE ESTADO_CASO (solo para PostgreSQL)
        print("\nä Paso 3: Actualizando enum 'estadocaso'...")

        try:
            # Verificar si los nuevos valores ya existen
            result = db.execute(text("SELECT enum_range(NULL::estadocaso)")).fetchone()
            valores_actuales = str(result[0]) if result else ""

            nuevos_valores = ['temporal', 'pagado', 'reembolsado']

            for valor in nuevos_valores:
                if valor not in valores_actuales:
                    sql = f"ALTER TYPE estadocaso ADD VALUE IF NOT EXISTS '{valor}'"
                    db.execute(text(sql))
                    db.commit()
                    print(f"    Agregado valor '{valor}' al enum")
                else:
                    print(f"     Valor '{valor}' ya existe en enum")

        except Exception as e:
            # Si no es PostgreSQL o enum no existe, omitir
            print(f"     Enum update no aplicable (probablemente SQLite): {str(e)[:50]}")
            db.rollback()

        # 4. CREAR TABLA SESIONES_DIARIAS
        print("\nä Paso 4: Creando tabla 'sesiones_diarias'...")

        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS sesiones_diarias (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    fecha DATE NOT NULL,
                    sesiones_creadas INTEGER DEFAULT 0 NOT NULL,
                    minutos_consumidos INTEGER DEFAULT 0 NOT NULL,
                    sesiones_base_permitidas INTEGER NOT NULL,
                    sesiones_extra_bonus INTEGER DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
            print("    Tabla 'sesiones_diarias' creada")

            # Crear ndices
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_sesiones_diarias_user_id ON sesiones_diarias(user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_sesiones_diarias_fecha ON sesiones_diarias(fecha)"))
            db.commit()
            print("    ndices creados")

        except Exception as e:
            if "already exists" in str(e).lower():
                print("     Tabla ya existe, omitiendo...")
                db.rollback()
            else:
                raise

        # 5. CREAR TABLA PAGOS
        print("\nä Paso 5: Creando tabla 'pagos'...")

        try:
            # Primero crear los enums necesarios (PostgreSQL)
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
                print("    Enums creados")
            except:
                # SQLite no soporta enums, usar VARCHAR
                db.rollback()
                print("     Enums no aplicables (SQLite)")

            # Crear tabla
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS pagos (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    caso_id INTEGER NOT NULL REFERENCES casos(id) ON DELETE CASCADE,
                    monto NUMERIC(10, 2) NOT NULL,
                    estado VARCHAR(50) DEFAULT 'pendiente' NOT NULL,
                    metodo_pago VARCHAR(50) DEFAULT 'simulado' NOT NULL,
                    referencia_pago VARCHAR(200),
                    referencia_reembolso VARCHAR(200),
                    fecha_pago TIMESTAMP,
                    fecha_reembolso TIMESTAMP,
                    motivo_reembolso TEXT,
                    notas_admin TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
            print("    Tabla 'pagos' creada")

            # Crear ndices
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_user_id ON pagos(user_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_caso_id ON pagos(caso_id)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago ON pagos(fecha_pago)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_pagos_referencia ON pagos(referencia_pago)"))
            db.commit()
            print("    ndices creados")

        except Exception as e:
            if "already exists" in str(e).lower():
                print("     Tabla ya existe, omitiendo...")
                db.rollback()
            else:
                raise

        # 6. MIGRAR DATOS EXISTENTES
        print("\nä Paso 6: Migrando datos existentes...")

        # Crear registros de pago para casos ya pagados
        casos_pagados = db.query(Caso).filter(
            Caso.documento_desbloqueado == True,
            Caso.fecha_pago != None
        ).all()

        print(f"   Ñ Encontrados {len(casos_pagados)} casos ya pagados")

        for caso in casos_pagados:
            # Verificar si ya existe un pago para este caso
            pago_existente = db.query(Pago).filter(Pago.caso_id == caso.id).first()

            if not pago_existente:
                nuevo_pago = Pago(
                    user_id=caso.user_id,
                    caso_id=caso.id,
                    monto=50000,  # Precio default
                    estado=EstadoPago.EXITOSO,
                    metodo_pago="simulado",
                    fecha_pago=caso.fecha_pago,
                    created_at=caso.fecha_pago,
                    updated_at=caso.fecha_pago
                )
                db.add(nuevo_pago)
                print(f"    Creado pago para caso {caso.id}")

        db.commit()
        print(f"    {len(casos_pagados)} pagos migrados")

        # Actualizar estado de casos pagados
        db.execute(text("""
            UPDATE casos
            SET estado = 'pagado'
            WHERE documento_desbloqueado = TRUE
            AND estado != 'pagado'
        """))
        db.commit()
        print("    Estados de casos actualizados")

        # Actualizar fecha de vencimiento para casos generados sin pagar
        db.execute(text("""
            UPDATE casos
            SET fecha_vencimiento = created_at + INTERVAL '14 days'
            WHERE estado = 'generado'
            AND documento_desbloqueado = FALSE
            AND fecha_vencimiento IS NULL
        """))
        db.commit()
        print("    Fechas de vencimiento actualizadas")

        # 7. RECALCULAR NIVELES DE USUARIOS
        print("\nä Paso 7: Recalculando niveles de usuarios...")

        usuarios = db.query(User).all()
        hace_30_dias = datetime.utcnow() - timedelta(days=30)

        for usuario in usuarios:
            # Contar pagos exitosos en ltimos 30 das
            pagos_mes = db.query(Pago).filter(
                Pago.user_id == usuario.id,
                Pago.estado == EstadoPago.EXITOSO,
                Pago.fecha_pago >= hace_30_dias
            ).count()

            # Calcular nivel
            if pagos_mes == 0:
                nivel = 0  # FREE
            elif pagos_mes == 1:
                nivel = 1  # BRONCE
            elif pagos_mes == 2:
                nivel = 2  # PLATA
            else:
                nivel = 3  # ORO

            usuario.pagos_ultimo_mes = pagos_mes
            usuario.nivel_usuario = nivel
            usuario.ultimo_recalculo_nivel = datetime.utcnow()

        db.commit()
        print(f"    {len(usuarios)} usuarios actualizados")

        # Mostrar distribucin de niveles
        niveles_count = {0: 0, 1: 0, 2: 0, 3: 0}
        for usuario in usuarios:
            niveles_count[usuario.nivel_usuario] += 1

        print("\nä Distribucin de niveles:")
        print(f"   FREE (0):   {niveles_count[0]} usuarios")
        print(f"   BRONCE (1): {niveles_count[1]} usuarios")
        print(f"   PLATA (2):  {niveles_count[2]} usuarios")
        print(f"   ORO (3):    {niveles_count[3]} usuarios")

        print("\n" + "=" * 60)
        print(" MIGRACIN COMPLETADA EXITOSAMENTE")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n ERROR en migracin: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   MIGRACION: SISTEMA DE NIVELES Y REEMBOLSOS")
    print("=" * 60)
    print("\nEsta migracion agregara:")
    print("   - Campos de niveles a tabla users")
    print("   - Campos de reembolsos a tabla casos")
    print("   - Tabla sesiones_diarias")
    print("   - Tabla pagos")
    print("   - Migracion de datos existentes")

    respuesta = input("\nContinuar con la migracion? (s/n): ")

    if respuesta.lower() == 's':
        success = migrate()
        sys.exit(0 if success else 1)
    else:
        print("\nMigracion cancelada")
        sys.exit(0)
