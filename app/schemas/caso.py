from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TipoDocumentoEnum(str, Enum):
    TUTELA = "TUTELA"
    DERECHO_PETICION = "DERECHO_PETICION"


class EstadoCasoEnum(str, Enum):
    TEMPORAL = "TEMPORAL"  # Sesión activa, conversando con avatar
    GENERADO = "GENERADO"  # Documento creado, esperando pago
    PAGADO = "PAGADO"  # Documento desbloqueado
    REEMBOLSADO = "REEMBOLSADO"  # Pago reembolsado
    # Estados legacy (mantener por compatibilidad)
    BORRADOR = "BORRADOR"
    FINALIZADO = "FINALIZADO"
    ABANDONADO = "ABANDONADO"


class CasoBase(BaseModel):
    """
    Schema base para casos - SIN validaciones estrictas.
    Las validaciones se hacen SOLO al momento de generar el documento.
    Esto permite guardar cualquier dato de la transcripción y que el usuario corrija en el formulario.
    """
    tipo_documento: TipoDocumentoEnum = TipoDocumentoEnum.TUTELA
    nombre_solicitante: Optional[str] = None
    identificacion_solicitante: Optional[str] = None
    direccion_solicitante: Optional[str] = None
    telefono_solicitante: Optional[str] = None
    email_solicitante: Optional[str] = None
    actua_en_representacion: bool = False
    nombre_representado: Optional[str] = None
    identificacion_representado: Optional[str] = None
    relacion_representado: Optional[str] = None
    tipo_representado: Optional[str] = None
    entidad_accionada: Optional[str] = None
    direccion_entidad: Optional[str] = None
    hechos: Optional[str] = None
    ciudad_de_los_hechos: Optional[str] = None
    derechos_vulnerados: Optional[str] = None
    pretensiones: Optional[str] = None
    fundamentos_derecho: Optional[str] = None
    pruebas: Optional[str] = None


class CasoCreate(CasoBase):
    pass


class CasoUpdate(BaseModel):
    tipo_documento: Optional[TipoDocumentoEnum] = None
    nombre_solicitante: Optional[str] = None
    identificacion_solicitante: Optional[str] = None
    direccion_solicitante: Optional[str] = None
    telefono_solicitante: Optional[str] = None
    email_solicitante: Optional[str] = None
    actua_en_representacion: Optional[bool] = None
    nombre_representado: Optional[str] = None
    identificacion_representado: Optional[str] = None
    relacion_representado: Optional[str] = None
    tipo_representado: Optional[str] = None
    entidad_accionada: Optional[str] = None
    direccion_entidad: Optional[str] = None
    hechos: Optional[str] = None
    ciudad_de_los_hechos: Optional[str] = None
    derechos_vulnerados: Optional[str] = None
    pretensiones: Optional[str] = None
    fundamentos_derecho: Optional[str] = None
    pruebas: Optional[str] = None
    estado: Optional[EstadoCasoEnum] = None
    documento_generado: Optional[str] = None


class CasoResponse(CasoBase):
    id: int
    user_id: int
    estado: EstadoCasoEnum
    documento_generado: Optional[str] = None
    documento_desbloqueado: bool = False
    fecha_pago: Optional[datetime] = None
    analisis_fortaleza: Optional[Dict[str, Any]] = None
    analisis_calidad: Optional[Dict[str, Any]] = None
    analisis_jurisprudencia: Optional[Dict[str, Any]] = None
    sugerencias_mejora: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CasoListResponse(BaseModel):
    id: int
    tipo_documento: TipoDocumentoEnum
    estado: EstadoCasoEnum
    nombre_solicitante: Optional[str] = None
    entidad_accionada: Optional[str] = None
    documento_desbloqueado: bool = False
    # Campos de reembolso
    reembolso_solicitado: bool = False
    fecha_solicitud_reembolso: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None
    evidencia_rechazo_url: Optional[str] = None
    fecha_reembolso: Optional[datetime] = None
    comentario_admin_reembolso: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
