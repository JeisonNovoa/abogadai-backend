import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User

def check_admins():
    """Verifica usuarios admin en la BD"""
    db = SessionLocal()
    try:
        # Obtener todos los usuarios
        users = db.query(User).all()

        print(f"\n=== TOTAL DE USUARIOS: {len(users)} ===\n")

        admins = []
        regular_users = []

        for user in users:
            if user.is_admin:
                admins.append(user)
            else:
                regular_users.append(user)

        # Mostrar admins
        print(f"ADMINISTRADORES ({len(admins)}):")
        if admins:
            for user in admins:
                print(f"  - ID: {user.id}")
                print(f"    Email: {user.email}")
                print(f"    Nombre: {user.nombre} {user.apellido if user.apellido else ''}")
                print(f"    is_admin: {user.is_admin}")
                print()
        else:
            print("  (No hay administradores)\n")

        # Mostrar usuarios regulares
        print(f"\nUSUARIOS REGULARES ({len(regular_users)}):")
        for user in regular_users:
            print(f"  - {user.email} (ID: {user.id})")

    finally:
        db.close()

if __name__ == "__main__":
    check_admins()
