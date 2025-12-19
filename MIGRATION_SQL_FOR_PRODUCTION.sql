-- =========================================================
-- SCRIPT DE MIGRACION A PRODUCCION
-- Base de datos: abogadai_db (Render)
-- Fecha: 2025-12-19
-- =========================================================
-- INSTRUCCIONES PARA EJECUTAR EN RENDER:
-- 1. Ve al panel de Render (https://dashboard.render.com/)
-- 2. Selecciona tu base de datos PostgreSQL
-- 3. Haz clic en "Shell" o "Connect"
-- 4. Copia y pega este script completo
-- 5. Presiona Enter para ejecutar
-- =========================================================

-- Verificar conexión
SELECT 'Conectado a la base de datos: ' || current_database() AS status;

-- =========================================================
-- MIGRACIÓN 1: Actualizar campos de caso (17-dic-2025)
-- =========================================================

-- 1.1. Agregar campo ciudad_de_los_hechos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'casos' AND column_name = 'ciudad_de_los_hechos'
    ) THEN
        ALTER TABLE casos ADD COLUMN ciudad_de_los_hechos VARCHAR(100);
        RAISE NOTICE 'Campo ciudad_de_los_hechos agregado exitosamente';
    ELSE
        RAISE NOTICE 'Campo ciudad_de_los_hechos ya existe, saltando...';
    END IF;
END $$;

-- 1.2. Eliminar campo representante_legal
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'casos' AND column_name = 'representante_legal'
    ) THEN
        ALTER TABLE casos DROP COLUMN representante_legal;
        RAISE NOTICE 'Campo representante_legal eliminado exitosamente';
    ELSE
        RAISE NOTICE 'Campo representante_legal no existe, saltando...';
    END IF;
END $$;

-- =========================================================
-- MIGRACIÓN 2: Agregar campos de paywall (19-dic-2025)
-- =========================================================

-- 2.1. Agregar campo documento_desbloqueado
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'casos' AND column_name = 'documento_desbloqueado'
    ) THEN
        ALTER TABLE casos ADD COLUMN documento_desbloqueado BOOLEAN DEFAULT FALSE NOT NULL;
        RAISE NOTICE 'Campo documento_desbloqueado agregado exitosamente';
    ELSE
        RAISE NOTICE 'Campo documento_desbloqueado ya existe, saltando...';
    END IF;
END $$;

-- 2.2. Agregar campo fecha_pago
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'casos' AND column_name = 'fecha_pago'
    ) THEN
        ALTER TABLE casos ADD COLUMN fecha_pago TIMESTAMP;
        RAISE NOTICE 'Campo fecha_pago agregado exitosamente';
    ELSE
        RAISE NOTICE 'Campo fecha_pago ya existe, saltando...';
    END IF;
END $$;

-- =========================================================
-- VERIFICACIÓN FINAL
-- =========================================================

-- Mostrar estructura actualizada de la tabla casos
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'casos'
ORDER BY ordinal_position;

-- Mostrar resumen
SELECT 'MIGRACIONES COMPLETADAS EXITOSAMENTE' AS status;

-- =========================================================
-- RESUMEN DE CAMBIOS APLICADOS:
-- - Campo 'ciudad_de_los_hechos' agregado (VARCHAR 100)
-- - Campo 'representante_legal' eliminado
-- - Campo 'documento_desbloqueado' agregado (BOOLEAN DEFAULT FALSE)
-- - Campo 'fecha_pago' agregado (TIMESTAMP)
-- =========================================================
