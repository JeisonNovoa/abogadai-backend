from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class SesionDiaria(Base):
    """
    Modelo para tracking de uso diario de sesiones por usuario
    Se resetea cada medianoche
    """
    __tablename__ = "sesiones_diarias"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)  # Fecha del día

    # Contadores
    sesiones_creadas = Column(Integer, default=0, nullable=False)  # Cuántas sesiones creó hoy
    minutos_consumidos = Column(Integer, default=0, nullable=False)  # Cuántos minutos usó hoy

    # Límites (se guardan para auditoría)
    sesiones_base_permitidas = Column(Integer, nullable=False)  # Límite base según su nivel
    sesiones_extra_bonus = Column(Integer, default=0, nullable=False)  # Sesiones extra por pagos de hoy

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = relationship("User", back_populates="sesiones_diarias")

    def sesiones_disponibles(self):
        """Calcula cuántas sesiones le quedan disponibles hoy"""
        total_permitidas = self.sesiones_base_permitidas + self.sesiones_extra_bonus
        return max(0, total_permitidas - self.sesiones_creadas)

    def minutos_disponibles(self, limite_minutos_totales):
        """Calcula cuántos minutos le quedan disponibles hoy"""
        if limite_minutos_totales is None:  # Sin límite (nivel ORO)
            return None
        return max(0, limite_minutos_totales - self.minutos_consumidos)
