from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..core.database import Base


class TipoDocumento(str, enum.Enum):
    TUTELA = "TUTELA"
    DERECHO_PETICION = "DERECHO_PETICION"


class EstadoCaso(str, enum.Enum):
    TEMPORAL = "TEMPORAL"  # Sesión activa, conversando con avatar
    GENERADO = "GENERADO"  # Documento creado, esperando pago
    PAGADO = "PAGADO"  # Documento desbloqueado
    REEMBOLSADO = "REEMBOLSADO"  # Pago reembolsado
    # Estados legacy (mantener por compatibilidad)
    BORRADOR = "BORRADOR"
    FINALIZADO = "FINALIZADO"
    ABANDONADO = "ABANDONADO"


class Caso(Base):
    __tablename__ = "casos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Tipo de documento
    tipo_documento = Column(SQLEnum(TipoDocumento), nullable=False, default=TipoDocumento.TUTELA)
    estado = Column(SQLEnum(EstadoCaso), nullable=False, default=EstadoCaso.BORRADOR)

    # Datos del solicitante
    nombre_solicitante = Column(String(200), nullable=True)
    identificacion_solicitante = Column(String(50), nullable=True)
    direccion_solicitante = Column(Text, nullable=True)
    telefono_solicitante = Column(String(50), nullable=True)
    email_solicitante = Column(String(200), nullable=True)

    # Representación de terceros
    actua_en_representacion = Column(Boolean, default=False, nullable=False)
    nombre_representado = Column(String(200), nullable=True)
    identificacion_representado = Column(String(50), nullable=True)
    relacion_representado = Column(String(100), nullable=True)  # madre, padre, cuidador, apoderado, etc.
    tipo_representado = Column(String(100), nullable=True)  # menor, adulto_mayor, persona_discapacidad, etc.

    # Datos de la entidad accionada
    entidad_accionada = Column(String(200), nullable=True)
    direccion_entidad = Column(Text, nullable=True)

    # Contenido del caso
    hechos = Column(Text, nullable=True)
    ciudad_de_los_hechos = Column(String(100), nullable=True)
    derechos_vulnerados = Column(Text, nullable=True)
    pretensiones = Column(Text, nullable=True)
    fundamentos_derecho = Column(Text, nullable=True)
    pruebas = Column(Text, nullable=True)  # Documentos y pruebas anexas

    # Documento generado
    documento_generado = Column(Text, nullable=True)

    # Sistema de paywall
    documento_desbloqueado = Column(Boolean, default=False, nullable=False)
    fecha_pago = Column(DateTime, nullable=True)
    fecha_vencimiento = Column(DateTime, nullable=True)  # 14 días después de generación

    # Sistema de reembolsos
    reembolso_solicitado = Column(Boolean, default=False, nullable=False)
    fecha_solicitud_reembolso = Column(DateTime, nullable=True)
    motivo_rechazo = Column(Text, nullable=True)  # Razón del rechazo legal
    evidencia_rechazo_url = Column(String(500), nullable=True)  # URL del documento de rechazo
    fecha_reembolso = Column(DateTime, nullable=True)
    comentario_admin_reembolso = Column(Text, nullable=True)
    historial_reembolsos = Column(JSON, nullable=True)  # Historial de todas las solicitudes/decisiones

    # Validación de subsidiariedad de la tutela (Art. 86 C.P.)
    hubo_derecho_peticion_previo = Column(Boolean, default=False, nullable=True)
    detalle_derecho_peticion_previo = Column(Text, nullable=True)
    tiene_perjuicio_irremediable = Column(Boolean, default=False, nullable=True)
    es_procedente_tutela = Column(Boolean, default=False, nullable=True)
    razon_improcedencia = Column(Text, nullable=True)

    # Análisis de IA
    analisis_fortaleza = Column(JSON, nullable=True)  # Análisis de fortaleza del caso
    analisis_calidad = Column(JSON, nullable=True)    # Análisis de calidad del documento
    analisis_jurisprudencia = Column(JSON, nullable=True)  # Validación de jurisprudencia
    sugerencias_mejora = Column(JSON, nullable=True)  # Sugerencias de mejora

    # Datos de sesión LiveKit (para integración con avatar)
    session_id = Column(String(100), nullable=True, index=True)  # UUID de la sesión
    room_name = Column(String(100), nullable=True)  # Nombre de la sala LiveKit
    fecha_inicio_sesion = Column(DateTime, nullable=True)  # Cuándo inició la sesión
    fecha_fin_sesion = Column(DateTime, nullable=True)  # Cuándo terminó la sesión

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = relationship("User", back_populates="casos")
    mensajes = relationship("Mensaje", back_populates="caso", cascade="all, delete-orphan")
    pagos = relationship("Pago", back_populates="caso", cascade="all, delete-orphan")
