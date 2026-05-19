import socket
import threading
from datetime import datetime
from db import init_db, guardar_mensaje, validar_usuario, crear_usuario
from protocol import send_packet, PacketReader

clientes = []
clientes_lock = threading.Lock()

_log_callback = None
_clients_callback = None


def set_callbacks(log_cb=None, clients_cb=None):
    global _log_callback, _clients_callback
    _log_callback = log_cb
    _clients_callback = clients_cb


def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if _log_callback:
        _log_callback(line)


def _notify_clients():
    if _clients_callback:
        with clientes_lock:
            snapshot = list(clientes)
        _clients_callback(snapshot)


def broadcast(packet, origen_conn=None):
    dead = []
    with clientes_lock:
        targets = list(clientes)
    for conn, usr in targets:
        if conn != origen_conn:
            try:
                send_packet(conn, packet)
            except OSError:
                dead.append((conn, usr))
    if dead:
        with clientes_lock:
            for item in dead:
                clientes.remove(item)


def send_server_message(texto):
    if not texto:
        return
    broadcast({"type": "message", "usuario": "Servidor", "texto": texto})
    _log(f"[Servidor -> todos] {texto}")


def _trama_from_packet(packet):
    return "|".join([
        "TRANSAC",
        packet.get("tipo", ""),
        packet.get("cuenta_origen", ""),
        packet.get("cuenta_destino", ""),
        packet.get("monto", ""),
        packet.get("concepto", ""),
    ])


def manejar_cliente(conn, addr):
    reader = PacketReader(conn)
    usuario = None

    try:
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
                    _log(f"Nuevo usuario registrado: {usr}")
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

        with clientes_lock:
            clientes.append((conn, usuario))
        _log(f"{usuario} conectado desde {addr[0]}:{addr[1]}")
        _notify_clients()

        while True:
            packet = reader.recv_packet()
            if not packet:
                break

            if packet.get("type") == "message":
                texto = packet.get("texto", "")
                guardar_mensaje(usuario, texto)
                _log(f"{usuario}: {texto}")
                broadcast({"type": "message", "usuario": usuario, "texto": texto}, conn)

            elif packet.get("type") == "transac":
                trama = _trama_from_packet(packet)
                guardar_mensaje(usuario, trama)
                _log(f"{usuario} -> {trama}")
                out = {k: v for k, v in packet.items()}
                out["usuario"] = usuario
                broadcast(out, conn)

    finally:
        conn.close()
        with clientes_lock:
            clientes[:] = [(c, u) for c, u in clientes if c != conn]
        if usuario:
            _log(f"{usuario} desconectado")
            _notify_clients()


def iniciar_servidor(host="0.0.0.0", port=5000):
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    _log(f"Servidor escuchando en {host}:{port}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    iniciar_servidor()
