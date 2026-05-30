import socket
import threading
from datetime import datetime
from db import (init_db, guardar_mensaje, validar_usuario, crear_usuario,
                obtener_productos, registrar_venta)
from protocol import send_packet, PacketReader

clientes = []
clientes_lock = threading.Lock()

_log_callback = None
_clients_callback = None
_error_callback = None


def set_callbacks(log_cb=None, clients_cb=None, error_cb=None):
    global _log_callback, _clients_callback, _error_callback
    _log_callback = log_cb
    _clients_callback = clients_cb
    _error_callback = error_cb


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


def _parse_trama(raw):
    """Parsea una trama cruda 'TRANSAC|...' y devuelve un dict o None si es inválida."""
    partes = raw.split("|")
    if partes[0] != "TRANSAC" or len(partes) != 6:
        return None
    return {"tipo": partes[1], "cuenta_origen": partes[2],
            "cuenta_destino": partes[3], "monto": partes[4], "concepto": partes[5]}


def manejar_cliente(conn, addr):
    reader = PacketReader(conn)
    usuario = None

    try:
        while usuario is None:
            packet = reader.recv_packet()
            if packet is None or isinstance(packet, str):
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
                    send_packet(conn, {"status": "ok", "usuario": usuario, "message": f"Bienvenido, {usuario}"})
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
            data = reader.recv_packet()
            if data is None:
                break

            if isinstance(data, str):
                campos = _parse_trama(data)
                if campos is None:
                    _log(f"{usuario} trama inválida: {data!r}")
                    continue
                guardar_mensaje(usuario, data)
                _log(f"{usuario} -> {data}")
                broadcast({"type": "transac", "usuario": usuario, **campos}, conn)
                continue

            if data.get("type") == "get_products":
                products = obtener_productos()
                send_packet(conn, {"type": "products_list", "products": products})

            elif data.get("type") == "sale":
                items = data.get("items", [])
                try:
                    venta_id, total, detalle = registrar_venta(usuario, items)
                    send_packet(conn, {
                        "type": "sale_result", "status": "ok",
                        "venta_id": venta_id, "total": total, "detalle": detalle,
                    })
                    broadcast({
                        "type": "sale_broadcast",
                        "usuario": usuario, "venta_id": venta_id, "total": total,
                    }, conn)
                    _log(f"{usuario} registró venta #{venta_id} por ${total:.2f}")
                except ValueError as e:
                    send_packet(conn, {"type": "sale_result", "status": "error", "message": str(e)})

            elif data.get("type") == "message":
                texto = data.get("texto", "")
                guardar_mensaje(usuario, texto)
                _log(f"{usuario}: {texto}")
                broadcast({"type": "message", "usuario": usuario, "texto": texto}, conn)

    finally:
        conn.close()
        with clientes_lock:
            clientes[:] = [(c, u) for c, u in clientes if c != conn]
        if usuario:
            _log(f"{usuario} desconectado")
            _notify_clients()


def iniciar_servidor(host="0.0.0.0", port=5000):
    init_db()
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
    except OSError as e:
        msg = (
            f"No se pudo abrir el puerto {port}:\n{e}\n\n"
            "En Windows esto suele deberse al Firewall o a falta de permisos.\n"
            "Ejecuta el servidor como Administrador o permite el acceso en el Firewall."
        )
        _log(f"ERROR: {e}")
        if _error_callback:
            _error_callback(msg)
        return
    _log(f"Servidor escuchando en {host}:{port}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    iniciar_servidor()
