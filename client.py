import socket
import threading
import sys
from protocol import send_packet, send_raw, PacketReader


if len(sys.argv) > 1:
    server = sys.argv[1]
else:
    server = "localhost"

TRANSAC_HELP = (
    "Uso: /transac TIPO|CUENTA_ORIGEN|CUENTA_DESTINO|MONTO|CONCEPTO\n"
    "Ej:  /transac PAGO|001|002|500.00|Pago renta"
)


def _trama_from_packet(packet):
    return "|".join([
        "TRANSAC",
        packet.get("tipo", ""),
        packet.get("cuenta_origen", ""),
        packet.get("cuenta_destino", ""),
        packet.get("monto", ""),
        packet.get("concepto", ""),
    ])


def recibir(reader):
    while True:
        try:
            packet = reader.recv_packet()
            if not packet:
                print("Conexión cerrada por el servidor.")
                break
            if packet.get("type") == "message":
                print(f"{packet['usuario']}: {packet['texto']}")
            elif packet.get("type") == "transac":
                usr = packet.get("usuario", "?")
                trama = _trama_from_packet(packet)
                print(f"[TRANSAC] {usr}: {trama}")
            elif "message" in packet:
                print(packet["message"])
        except (OSError, ConnectionResetError):
            break


def parse_transac(comando):
    """
    Parsea '/transac TIPO|ORIGEN|DESTINO|MONTO|CONCEPTO'.
    Devuelve el packet dict o None si el formato es inválido.
    """
    partes = comando[len("/transac"):].strip().split("|")
    if len(partes) != 5:
        return None
    keys = ("tipo", "cuenta_origen", "cuenta_destino", "monto", "concepto")
    packet = {"type": "transac"}
    packet.update(dict(zip(keys, (p.strip() for p in partes))))
    return packet


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

print("Conectado. Escribe un mensaje o usa /transac para enviar una transacción.")
print(TRANSAC_HELP)

threading.Thread(target=recibir, args=(reader,), daemon=True).start()

try:
    while True:
        msg = input("")
        if not msg:
            continue
        if msg.startswith("/transac"):
            packet = parse_transac(msg)
            if packet is None:
                print(TRANSAC_HELP)
            else:
                trama = "|".join(["TRANSAC", packet["tipo"], packet["cuenta_origen"],
                                   packet["cuenta_destino"], packet["monto"], packet["concepto"]])
                send_raw(client, trama)
                print(f"[TRANSAC] {usuario}: {trama}")
        else:
            send_packet(client, {"type": "message", "texto": msg})
except (KeyboardInterrupt, EOFError):
    pass
finally:
    client.close()
