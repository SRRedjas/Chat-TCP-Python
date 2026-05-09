import socket
import threading
import sys
from protocol import send_packet, PacketReader


if len(sys.argv) > 1:
    server = sys.argv[1]
else:
    server = "localhost"


def recibir(reader):
    while True:
        try:
            packet = reader.recv_packet()
            if not packet:
                print("Conexión cerrada por el servidor.")
                break
            if packet.get("type") == "message":
                print(f"{packet['usuario']}: {packet['texto']}")
            elif "message" in packet:
                print(packet["message"])
        except (OSError, ConnectionResetError):
            break


def autenticar(conn, reader):
    while True:
        print("\n1. Iniciar sesión")
        print("2. Registrarse")
        print("0. Salir")
        opcion = input("Elige una opción: ").strip()

        if opcion == "0":
            return None

        if opcion not in ("1", "2"):
            print("Opción inválida.")
            continue

        usuario = input("Usuario: ").strip()
        password = input("Contraseña: ").strip()

        if not usuario or not password:
            print("Usuario y contraseña son obligatorios.")
            continue

        if opcion == "2":
            send_packet(conn, {"type": "register", "usuario": usuario, "password": password})
            resp = reader.recv_packet()
            print(resp.get("message", ""))
            # Tras registrarse vuelve al menú para iniciar sesión

        elif opcion == "1":
            send_packet(conn, {"type": "login", "usuario": usuario, "password": password})
            resp = reader.recv_packet()
            print(resp.get("message", ""))
            if resp.get("status") == "ok":
                return usuario


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server, 5000))
reader = PacketReader(client)

usuario = autenticar(client, reader)
if not usuario:
    client.close()
    sys.exit(0)

threading.Thread(target=recibir, args=(reader,), daemon=True).start()

try:
    while True:
        msg = input("")
        if msg:
            send_packet(client, {"type": "message", "texto": msg})
except (KeyboardInterrupt, EOFError):
    pass
finally:
    client.close()
