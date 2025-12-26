"""
Script de prueba completa del flujo de reembolsos
Simula el ciclo completo: solicitar -> rechazar -> re-solicitar -> aprobar
"""

from app.core.database import SessionLocal
from app.models.caso import Caso, EstadoCaso
from app.models.pago import Pago, EstadoPago
from app.services import pago_service
import json

def test_flujo_completo():
    db = SessionLocal()

    # Buscar un caso pagado para probar
    caso = db.query(Caso).filter(
        Caso.estado == EstadoCaso.PAGADO,
        Caso.reembolso_solicitado == False
    ).first()

    if not caso:
        print("No hay casos pagados disponibles para probar")
        db.close()
        return

    caso_id = caso.id
    print(f"\n{'='*60}")
    print(f"PRUEBA COMPLETA DE FLUJO DE REEMBOLSOS - CASO #{caso_id}")
    print(f"{'='*60}\n")

    # 1. Primera solicitud de reembolso
    print("1. PRIMERA SOLICITUD DE REEMBOLSO")
    print("-" * 60)
    try:
        resultado = pago_service.solicitar_reembolso(
            caso_id=caso_id,
            motivo="Primera solicitud - documento rechazado",
            evidencia_url="/uploads/evidencia1.pdf",
            db=db
        )
        print(f"OK - Solicitud creada: {resultado['fecha_solicitud']}")
        print(f"Es re-solicitud: {resultado['es_resolicitud']}")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 2. Rechazar primera solicitud
    print("\n2. RECHAZAR PRIMERA SOLICITUD")
    print("-" * 60)
    try:
        resultado = pago_service.procesar_reembolso(
            caso_id=caso_id,
            aprobar=False,
            comentario_admin="Evidencia insuficiente - primera vez",
            db=db
        )
        print(f"OK - Solicitud rechazada")
        print(f"Puede re-solicitar: {resultado['puede_resolicitar']}")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 3. Segunda solicitud de reembolso (re-solicitud)
    print("\n3. SEGUNDA SOLICITUD (RE-SOLICITUD)")
    print("-" * 60)
    try:
        resultado = pago_service.solicitar_reembolso(
            caso_id=caso_id,
            motivo="Segunda solicitud - nueva evidencia",
            evidencia_url="/uploads/evidencia2.pdf",
            db=db
        )
        print(f"OK - Re-solicitud creada: {resultado['fecha_solicitud']}")
        print(f"Es re-solicitud: {resultado['es_resolicitud']}")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 4. Rechazar segunda solicitud
    print("\n4. RECHAZAR SEGUNDA SOLICITUD")
    print("-" * 60)
    try:
        resultado = pago_service.procesar_reembolso(
            caso_id=caso_id,
            aprobar=False,
            comentario_admin="Documento incompleto - segunda vez",
            db=db
        )
        print(f"OK - Segunda solicitud rechazada")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 5. Tercera solicitud de reembolso
    print("\n5. TERCERA SOLICITUD")
    print("-" * 60)
    try:
        resultado = pago_service.solicitar_reembolso(
            caso_id=caso_id,
            motivo="Tercera solicitud - evidencia completa ahora",
            evidencia_url="/uploads/evidencia3.pdf",
            db=db
        )
        print(f"OK - Tercera solicitud creada: {resultado['fecha_solicitud']}")
        print(f"Es re-solicitud: {resultado['es_resolicitud']}")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 6. Aprobar tercera solicitud
    print("\n6. APROBAR TERCERA SOLICITUD")
    print("-" * 60)
    try:
        resultado = pago_service.procesar_reembolso(
            caso_id=caso_id,
            aprobar=True,
            comentario_admin="Aprobado - evidencia valida",
            db=db
        )
        print(f"OK - Solicitud aprobada")
        print(f"Monto reembolsado: ${resultado['monto']}")
        print(f"Fecha reembolso: {resultado['fecha_reembolso']}")
    except Exception as e:
        print(f"ERROR: {e}")
        db.close()
        return

    # 7. Verificar estado final
    print(f"\n7. VERIFICACION FINAL")
    print("-" * 60)
    db.refresh(caso)
    print(f"Estado final del caso: {caso.estado}")
    print(f"Reembolso solicitado: {caso.reembolso_solicitado}")
    print(f"Documento desbloqueado: {caso.documento_desbloqueado}")
    print(f"\nHISTORIAL COMPLETO ({len(caso.historial_reembolsos or [])} entradas):")
    for i, entry in enumerate(caso.historial_reembolsos or [], 1):
        print(f"\n  Entrada {i}:")
        print(f"    Tipo: {entry['tipo']}")
        print(f"    Motivo usuario: {entry['motivo_usuario']}")
        print(f"    Comentario admin: {entry['comentario_admin']}")
        print(f"    Fecha decision: {entry['fecha_decision']}")

    print(f"\n{'='*60}")
    print("PRUEBA COMPLETADA EXITOSAMENTE")
    print(f"{'='*60}\n")

    db.close()

if __name__ == "__main__":
    test_flujo_completo()
