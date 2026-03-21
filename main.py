import socket
import threading
from db import init_db, guardar_mensaje, validar_usuario

clientes = []

def manejar_cliente(conn, addr):
    conn.sendall(b"Usuario:")

    usuario = conn.recv(1024).decode().strip()
    #usuario = f"{addr[0]}:{addr[1]}"
    conn.sendall(b"Clave:")
    password = conn.recv(1024).decode().strip()

    if not validar_usuario(usuario, password):
        conn.sendall(b"Credenciales incorrectas. conexion cerrada. \n")
        conn.close()
        return 
    
    print(usuario)
    conn.sendall(b"Bienvenido")

    while True:
        msg = conn.recv(1024).decode()
        if not msg:
            break
        guardar_mensaje(usuario, msg)
        print(f"{usuario}: {msg}")
        # reenviar a todos los clientes
        for c in clientes:
            if c != conn:
                
                c.sendall(f"{usuario}: {msg}".encode())
    conn.close()

def iniciar_servidor():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5000))
    server.listen()
    print("Servidor escuchando en puerto 5000...")
    while True:
        conn, addr = server.accept()
        clientes.append(conn)
        print(clientes)
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()

iniciar_servidor()
