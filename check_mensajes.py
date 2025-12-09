from app.core.database import SessionLocal
from app.models.mensaje import Mensaje
from app.models.caso import Caso

db = SessionLocal()

print("=== VERIFICACIÓN DE MENSAJES POR CASO ===\n")

for caso_id in [2, 3]:
    mensajes = db.query(Mensaje).filter(Mensaje.caso_id == caso_id).all()
    print(f"Caso {caso_id}: {len(mensajes)} mensajes")
    for i, m in enumerate(mensajes[:5], 1):
        print(f"  [{i}] {m.remitente}: {m.texto[:80]}...")
    print()

db.close()
