from getpass import getpass

from database.usuarios import autenticar_usuario

print("\n=== PRUEBA DE AUTENTICACION REPORTESPRO ===")

correo = input("Correo de la cuenta: ").strip()
password = getpass("Contraseña: ")

usuario = autenticar_usuario(correo, password)

if usuario is None:
    print("\nRESULTADO: AUTENTICACION RECHAZADA")
else:
    print("\nRESULTADO: AUTENTICACION CORRECTA")
    print("ID del usuario:", usuario["id"])
    print("Nombre:", usuario["nombre"])
