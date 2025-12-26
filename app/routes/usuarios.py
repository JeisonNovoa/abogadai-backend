"""
Endpoints de Usuarios - Niveles y Beneficios
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.user import User
from .auth import get_current_user
from ..services import nivel_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/mi-nivel")
async def obtener_mi_nivel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 Retorna nivel actual del usuario y beneficios

    Información incluida:
    - Nivel actual (0-3)
    - Nombre del nivel (FREE, BRONCE, PLATA, ORO)
    - Límites de sesión según nivel
    - Cantidad de pagos del último mes
    - Sesiones extra disponibles hoy
    """
    limites = nivel_service.obtener_limites_usuario(current_user.id, db)

    # Calcular siguiente nivel
    nivel_actual = limites["nivel"]
    siguiente_nivel = None
    pagos_hasta_siguiente = 0

    if nivel_actual == 0:  # FREE → BRONCE (necesita 1 pago)
        siguiente_nivel = "BRONCE"
        pagos_hasta_siguiente = 1
    elif nivel_actual == 1:  # BRONCE → PLATA (necesita 2 pagos total)
        siguiente_nivel = "PLATA"
        pagos_hasta_siguiente = 2
    elif nivel_actual == 2:  # PLATA → ORO (necesita 3 pagos total)
        siguiente_nivel = "ORO"
        pagos_hasta_siguiente = 3
    # Nivel 3 (ORO) no tiene siguiente nivel

    # Campos compatibles con el frontend
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        # Frontend espera "nivel_actual" en lugar de "nivel"
        "nivel_actual": limites["nombre_nivel"],  # "FREE", "BRONCE", "PLATA", "ORO"
        "nombre_nivel": limites["nombre_nivel"],
        "pagos_ultimo_mes": current_user.pagos_ultimo_mes,
        "sesiones_extra_hoy": current_user.sesiones_extra_hoy,
        # Frontend espera estos campos directos
        "sesiones_maximas": limites["sesiones_dia"],
        "minutos_maximos": limites["min_sesion"],
        "max_docs_sin_pagar": 3,  # Todos los niveles permiten 3 docs sin pagar
        "precio_documento": 50000,  # Precio estándar en COP
        # Progreso hacia siguiente nivel
        "siguiente_nivel": siguiente_nivel,
        "pagos_en_nivel": current_user.pagos_ultimo_mes,
        "pagos_hasta_siguiente": pagos_hasta_siguiente,
        # Mantener compatibilidad con versión anterior
        "limites": {
            "sesiones_dia": limites["sesiones_dia"],
            "min_sesion": limites["min_sesion"],
            "min_totales": limites["min_totales"]
        },
        "ultimo_recalculo": current_user.ultimo_recalculo_nivel
    }


@router.get("/beneficios-niveles")
async def obtener_beneficios_niveles():
    """
    📋 Retorna tabla de beneficios de todos los niveles

    Endpoint público (no requiere autenticación)
    Útil para mostrar tabla de precios/beneficios en landing page
    """
    return {
        "niveles": [
            {
                "nivel": 0,
                "nombre": "FREE",
                "requisito": "Sin pagos en últimos 30 días",
                "color": "#9CA3AF",
                "beneficios": {
                    "sesiones_dia": 3,
                    "min_sesion": 10,
                    "min_totales": 30,
                    "descripcion": "Perfecto para probar la plataforma"
                }
            },
            {
                "nivel": 1,
                "nombre": "BRONCE",
                "requisito": "1 pago en últimos 30 días",
                "color": "#CD7F32",
                "beneficios": {
                    "sesiones_dia": 5,
                    "min_sesion": 10,
                    "min_totales": 50,
                    "descripcion": "Para usuarios ocasionales"
                }
            },
            {
                "nivel": 2,
                "nombre": "PLATA",
                "requisito": "2 pagos en últimos 30 días",
                "color": "#C0C0C0",
                "beneficios": {
                    "sesiones_dia": 7,
                    "min_sesion": 10,
                    "min_totales": 70,
                    "descripcion": "Para usuarios frecuentes"
                }
            },
            {
                "nivel": 3,
                "nombre": "ORO",
                "requisito": "3+ pagos en últimos 30 días",
                "color": "#FFD700",
                "beneficios": {
                    "sesiones_dia": 10,
                    "min_sesion": 15,
                    "min_totales": None,
                    "descripcion": "Libertad total - sin límite de minutos totales"
                }
            }
        ],
        "bonus_por_pago": {
            "sesiones_extra": 2,
            "vigencia": "Mismo día del pago",
            "descripcion": "Cada pago desbloquea +2 sesiones bonus inmediatas"
        },
        "politica_reembolso": {
            "condicion": "Documento legalmente rechazado (tutela/derecho petición)",
            "evidencia_requerida": "Documento oficial de rechazo",
            "proceso": "Solicitud manual revisada por admin"
        }
    }
