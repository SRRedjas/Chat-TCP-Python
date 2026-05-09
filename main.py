import socket
import threading
from db import init_db, guardar_mensaje, validar_usuario, crear_usuario
from protocol import send_packet, PacketReader

clientes = []  # lista de (conn, usuario)
clientes_lock = threading.Lock()


def broadcast(packet, origen_conn):
    dead = []
    with clientes_lock:
        for conn, usr in clientes:
            if conn != origen_conn:
                try:
                    send_packet(conn, packet)
                except OSError:
                    dead.append((conn, usr))
        for item in dead:
            clientes.remove(item)


def manejar_cliente(conn, addr):
    reader = PacketReader(conn)
    usuario = None

    try:
        # Fase de autenticación: loop hasta login exitoso
        while usuario is None:
            packet = reader.recv_packet()
            if not packet:
                return

            tipo = packet.get("type")
            usr = packet.get("usuario", "").strip()
            pwd = packet.get("password", "").strip()

            if tipo == "register":
                try:
                    crear_usuario(usr, pwd)
                    send_packet(conn, {"status": "ok", "message": "Usuario registrado. Ahora inicia sesión."})
                except Exception:
                    send_packet(conn, {"status": "error", "message": "El usuario ya existe."})

            elif tipo == "login":
                if validar_usuario(usr, pwd):
                    usuario = usr
                    send_packet(conn, {"status": "ok", "message": f"Bienvenido, {usuario}"})
                else:
                    send_packet(conn, {"status": "error", "message": "Credenciales incorrectas."})

            else:
                send_packet(conn, {"status": "error", "message": "Operación no reconocida."})
                return

        # Fase de chat
        with clientes_lock:
            clientes.append((conn, usuario))
        print(f"{usuario} conectado desde {addr[0]}:{addr[1]}")

        while True:
            packet = reader.recv_packet()
            if not packet:
                break
            if packet.get("type") == "message":
                texto = packet.get("texto", "")
                guardar_mensaje(usuario, texto)
                print(f"{usuario}: {texto}")
                broadcast({"type": "message", "usuario": usuario, "texto": texto}, conn)

    finally:
        conn.close()
        with clientes_lock:
            clientes[:] = [(c, u) for c, u in clientes if c != conn]
        if usuario:
            print(f"{usuario} desconectado")


def iniciar_servidor():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 5000))
    server.listen()
    print("Servidor escuchando en puerto 5000...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    iniciar_servidor()
