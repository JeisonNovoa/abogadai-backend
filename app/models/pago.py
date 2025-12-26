from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..core.database import Base


class EstadoPago(str, enum.Enum):
    PENDIENTE = "pendiente"
    EXITOSO = "exitoso"
    FALLIDO = "fallido"
    REEMBOLSADO = "reembolsado"


class MetodoPago(str, enum.Enum):
    SIMULADO = "simulado"
    MERCADOPAGO = "mercadopago"
    WOMPI = "wompi"
    PSE = "pse"
    TARJETA = "tarjeta"


class Pago(Base):
    """
    Modelo para historial de pagos y reembolsos
    """
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    caso_id = Column(Integer, ForeignKey("casos.id"), nullable=False, index=True)

    # Datos del pago
    monto = Column(Numeric(10, 2), nullable=False)  # Monto en COP (ej: 50000.00)
    estado = Column(SQLEnum(EstadoPago), nullable=False, default=EstadoPago.PENDIENTE, index=True)
    metodo_pago = Column(SQLEnum(MetodoPago), nullable=False, default=MetodoPago.SIMULADO)

    # Referencias externas
    referencia_pago = Column(String(200), nullable=True, index=True)  # ID de la transacción en pasarela
    referencia_reembolso = Column(String(200), nullable=True)  # ID del reembolso en pasarela

    # Fechas
    fecha_pago = Column(DateTime, nullable=True, index=True)  # Cuándo se completó el pago
    fecha_reembolso = Column(DateTime, nullable=True)  # Cuándo se procesó el reembolso

    # Información adicional
    motivo_reembolso = Column(Text, nullable=True)
    notas_admin = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = relationship("User", back_populates="pagos")
    caso = relationship("Caso", back_populates="pagos")

    def esta_pagado(self):
        """Verifica si el pago fue exitoso"""
        return self.estado == EstadoPago.EXITOSO

    def fue_reembolsado(self):
        """Verifica si el pago fue reembolsado"""
        return self.estado == EstadoPago.REEMBOLSADO
