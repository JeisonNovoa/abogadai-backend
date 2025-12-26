from app.core.database import SessionLocal
from app.models.caso import Caso, EstadoCaso

db = SessionLocal()

print("=== ANÁLISIS DE REEMBOLSOS ===\n")

# Casos con solicitud pendiente
pendientes = db.query(Caso).filter(
    Caso.reembolso_solicitado == True,
    Caso.fecha_reembolso == None
).all()
print(f"Pendientes ({len(pendientes)}):")
for c in pendientes:
    print(f"  Caso {c.id}: estado={c.estado}")

# Casos reembolsados (aprobados)
aprobados = db.query(Caso).filter(
    Caso.estado == EstadoCaso.REEMBOLSADO
).all()
print(f"\nAprobados ({len(aprobados)}):")
for c in aprobados:
    print(f"  Caso {c.id}: reembolso_solicitado={c.reembolso_solicitado}, fecha_reembolso={c.fecha_reembolso}")

# Casos rechazados
rechazados = db.query(Caso).filter(
    Caso.reembolso_solicitado == False,
    Caso.fecha_reembolso != None,
    Caso.estado != EstadoCaso.REEMBOLSADO
).all()
print(f"\nRechazados ({len(rechazados)}):")
for c in rechazados:
    print(f"  Caso {c.id}: estado={c.estado}, fecha_reembolso={c.fecha_reembolso}")

# Total
total = len(pendientes) + len(aprobados) + len(rechazados)
print(f"\nTotal: {total}")

db.close()
