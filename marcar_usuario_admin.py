"""
Script para marcar un usuario como administrador

Uso:
    python marcar_usuario_admin.py EMAIL_DEL_USUARIO

Ejemplo:
    python marcar_usuario_admin.py usuario@ejemplo.com
"""

import sys
from app.core.database import SessionLocal
from app.models.user import User


def marcar_como_admin(email: str):
    """Marca un usuario como administrador"""
    db = SessionLocal()

    try:
        # Buscar usuario por email
        usuario = db.query(User).filter(User.email == email).first()

        if not usuario:
            print(f"\n❌ ERROR: No se encontró ningún usuario con email '{email}'")
            print("\n💡 Asegúrate de escribir el email correcto (el que usas para hacer login)")
            return False

        # Verificar si ya es admin
        if usuario.is_admin:
            print(f"\n✅ El usuario '{email}' ya es administrador")
            return True

        # Marcar como admin
        usuario.is_admin = True
        db.commit()

        print(f"\n✅ ¡Éxito! El usuario '{email}' ahora es administrador")
        print(f"\n📋 Información del usuario:")
        print(f"   - ID: {usuario.id}")
        print(f"   - Nombre: {usuario.nombre} {usuario.apellido}")
        print(f"   - Email: {usuario.email}")
        print(f"   - Es admin: {usuario.is_admin}")
        print(f"\n🔐 Ahora puedes acceder al panel de admin en:")
        print(f"   http://localhost:5173/app/admin/reembolsos")
        print(f"   http://localhost:5173/app/admin/metricas")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        db.rollback()
        return False

    finally:
        db.close()


def listar_usuarios():
    """Lista todos los usuarios para ayudar a encontrar el email correcto"""
    db = SessionLocal()

    try:
        usuarios = db.query(User).all()

        if not usuarios:
            print("\n❌ No hay usuarios en la base de datos")
            return

        print("\n📋 Usuarios registrados:")
        print("-" * 80)
        for usuario in usuarios:
            admin_badge = "👑 ADMIN" if usuario.is_admin else "👤 Usuario"
            print(f"{admin_badge} | {usuario.email} | {usuario.nombre} {usuario.apellido} (ID: {usuario.id})")
        print("-" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔧 MARCAR USUARIO COMO ADMINISTRADOR")
    print("=" * 80)

    # Si no se proporciona email, mostrar ayuda
    if len(sys.argv) < 2:
        print("\n❌ ERROR: Debes proporcionar el email del usuario")
        print("\n📖 Uso:")
        print("   python marcar_usuario_admin.py EMAIL_DEL_USUARIO")
        print("\n📝 Ejemplo:")
        print("   python marcar_usuario_admin.py usuario@ejemplo.com")
        print("\n" + "-" * 80)
        print("📋 Para ver la lista de usuarios disponibles, ejecuta:")
        print("   python marcar_usuario_admin.py --listar")
        print("=" * 80 + "\n")
        sys.exit(1)

    email_arg = sys.argv[1]

    # Opción para listar usuarios
    if email_arg in ["--listar", "-l", "--list"]:
        listar_usuarios()
        print("\n💡 Ahora ejecuta el script con el email del usuario que quieres hacer admin:")
        print("   python marcar_usuario_admin.py EMAIL_DEL_USUARIO")
        print("=" * 80 + "\n")
        sys.exit(0)

    # Marcar usuario como admin
    exito = marcar_como_admin(email_arg)

    print("=" * 80 + "\n")

    sys.exit(0 if exito else 1)
