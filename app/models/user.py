from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Campos de perfil
    identificacion = Column(String(50), nullable=True, index=True)
    direccion = Column(Text, nullable=True)
    telefono = Column(String(50), nullable=True)
    perfil_completo = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Sistema de niveles y límites
    nivel_usuario = Column(Integer, default=0, nullable=False)  # 0=Free, 1=Bronce, 2=Plata, 3=Oro
    pagos_ultimo_mes = Column(Integer, default=0, nullable=False)  # Contador de pagos en últimos 30 días
    ultimo_recalculo_nivel = Column(DateTime, nullable=True)  # Última vez que se recalculó el nivel
    sesiones_extra_hoy = Column(Integer, default=0, nullable=False)  # Sesiones bonus por pagos de hoy

    # Relaciones
    casos = relationship("Caso", back_populates="user")
    sesiones_diarias = relationship("SesionDiaria", back_populates="user", cascade="all, delete-orphan")
    pagos = relationship("Pago", back_populates="user", cascade="all, delete-orphan")

    def tiene_perfil_completo(self):
        """Verifica si todos los campos del perfil están completos"""
        return all([
            self.nombre,
            self.apellido,
            self.email,
            self.identificacion,
            self.direccion,
            self.telefono
        ])

    def obtener_nombre_nivel(self):
        """Retorna el nombre del nivel del usuario"""
        niveles = {
            0: "FREE",
            1: "BRONCE",
            2: "PLATA",
            3: "ORO"
        }
        return niveles.get(self.nivel_usuario, "FREE")

    def obtener_limites_sesion(self):
        """Retorna los límites de sesión según el nivel del usuario"""
        limites = {
            0: {"sesiones_dia": 3, "min_sesion": 10, "min_totales": 30},
            1: {"sesiones_dia": 5, "min_sesion": 10, "min_totales": 50},
            2: {"sesiones_dia": 7, "min_sesion": 10, "min_totales": 70},
            3: {"sesiones_dia": 10, "min_sesion": 15, "min_totales": None}  # Sin límite total
        }
        return limites.get(self.nivel_usuario, limites[0])
