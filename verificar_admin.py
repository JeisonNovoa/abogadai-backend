"""
Script simple para verificar el estado de is_admin de un usuario

Uso: Abre PostgreSQL y ejecuta la query directamente
"""

print("""
=" * 80)
🔍 VERIFICAR ESTADO DE ADMIN
=" * 80)

Para verificar si tu usuario es admin, ejecuta esta query en PostgreSQL:

1. Abre pgAdmin o psql
2. Conéctate a tu base de datos
3. Ejecuta:

SELECT id, email, nombre, apellido, is_admin
FROM users
ORDER BY id;

=" * 80)

Si is_admin es FALSE para tu usuario, ejecútalo esto para hacerlo admin:

UPDATE users
SET is_admin = true
WHERE email = 'TU_EMAIL_AQUI';

Luego verifica de nuevo:

SELECT id, email, nombre, apellido, is_admin
FROM users
WHERE email = 'TU_EMAIL_AQUI';

=" * 80)

IMPORTANTE DESPUÉS DE CAMBIAR:
1. Cierra sesión en la aplicación web
2. Limpia el caché del navegador (Ctrl + Shift + R)
3. Inicia sesión de nuevo
4. Abre la consola del navegador (F12)
5. Escribe: console.log(JSON.parse(localStorage.getItem('user')))
6. Verifica que is_admin sea true

=" * 80)
""")
