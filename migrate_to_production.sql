-- =========================================================
-- SCRIPT DE MIGRACION A PRODUCCION
-- Base de datos: abogadai_db (Render)
-- Fecha: 2025-12-19
-- =========================================================
-- Este script aplica las migraciones pendientes a la BD de producción
--
-- CAMBIOS INCLUIDOS:
-- 1. Agregar campo ciudad_de_los_hechos (migración 17-dic-2025)
-- 2. Eliminar campo representante_legal (migración 17-dic-2025)
-- 3. Agregar campo documento_desbloqueado (migración 19-dic-2025)
-- 4. Agregar campo fecha_pago (migración 19-dic-2025)
-- =========================================================

BEGIN;

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

-- Mostrar estructura actual de la tabla casos
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'casos'
ORDER BY ordinal_position;

COMMIT;

-- =========================================================
-- FIN DEL SCRIPT
-- =========================================================
-- Si todo salió bien, deberías ver los siguientes mensajes:
-- - Campo ciudad_de_los_hechos agregado exitosamente
-- - Campo representante_legal eliminado exitosamente
-- - Campo documento_desbloqueado agregado exitosamente
-- - Campo fecha_pago agregado exitosamente
-- =========================================================
