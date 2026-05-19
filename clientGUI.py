import socket
import threading
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox
from protocol import send_packet, send_raw, PacketReader


if len(sys.argv) > 1:
    server = sys.argv[1]
else:
    server = "localhost"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server, 5000))
reader = PacketReader(client)

nombre_usuario = None


def _append_text(text_area, msg):
    text_area.config(state=tk.NORMAL)
    text_area.insert(tk.END, msg + "\n")
    text_area.yview(tk.END)
    text_area.config(state=tk.DISABLED)


def _trama_from_packet(packet):
    return "|".join([
        "TRANSAC",
        packet.get("tipo", ""),
        packet.get("cuenta_origen", ""),
        packet.get("cuenta_destino", ""),
        packet.get("monto", ""),
        packet.get("concepto", ""),
    ])


def recibir(text_area):
    while True:
        try:
            packet = reader.recv_packet()
            if not packet:
                break
            if packet.get("type") == "message":
                msg = f"{packet['usuario']}: {packet['texto']}"
                root.after(0, _append_text, text_area, msg)
            elif packet.get("type") == "transac":
                usr = packet.get("usuario", "?")
                trama = _trama_from_packet(packet)
                root.after(0, _append_text, text_area, f"[TRANSAC] {usr}: {trama}")
            elif "message" in packet:
                root.after(0, _append_text, text_area, packet["message"])
        except (OSError, ConnectionResetError):
            break


def enviar_mensaje(entry, text_area):
    msg = entry.get().strip()
    if not msg:
        return
    send_packet(client, {"type": "message", "texto": msg})
    root.after(0, _append_text, text_area, f"{nombre_usuario}: {msg}")
    entry.delete(0, tk.END)


def abrir_dialogo_transac(text_area):
    win = tk.Toplevel(root)
    win.title("Nueva Transacción")
    win.resizable(False, False)
    win.grab_set()

    campos = [
        ("Tipo de operación:", "tipo"),
        ("Cuenta origen:",     "cuenta_origen"),
        ("Cuenta destino:",    "cuenta_destino"),
        ("Monto:",             "monto"),
        ("Concepto:",          "concepto"),
    ]
    entries = {}

    for row, (label, key) in enumerate(campos):
        tk.Label(win, text=label, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=14, pady=4)
        e = tk.Entry(win, width=30)
        e.grid(row=row, column=1, padx=14, pady=4)
        entries[key] = e

    entries["tipo"].insert(0, "PAGO")
    entries["tipo"].focus()

    def enviar_transac():
        valores = {k: e.get().strip() for k, e in entries.items()}
        if not all(valores.values()):
            messagebox.showerror("Error", "Todos los campos son obligatorios.", parent=win)
            return
        trama = "|".join(["TRANSAC", valores["tipo"], valores["cuenta_origen"],
                           valores["cuenta_destino"], valores["monto"], valores["concepto"]])
        send_raw(client, trama)
        root.after(0, _append_text, text_area, f"[TRANSAC] {nombre_usuario}: {trama}")
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.grid(row=len(campos), column=0, columnspan=2, pady=10)
    tk.Button(btn_frame, text="Enviar", width=14, command=enviar_transac).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Cancelar", width=14, command=win.destroy).pack(side=tk.LEFT, padx=6)

    win.bind("<Return>", lambda _e: enviar_transac())


def mostrar_chat():
    login_frame.pack_forget()

    chat_frame = tk.Frame(root)
    chat_frame.pack(fill=tk.BOTH, expand=True)

    text_area = scrolledtext.ScrolledText(
        chat_frame, wrap=tk.WORD, state=tk.DISABLED, width=55, height=20
    )
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    bottom = tk.Frame(chat_frame)
    bottom.pack(fill=tk.X, padx=10, pady=5)

    entry = tk.Entry(bottom)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    entry.bind("<Return>", lambda _e: enviar_mensaje(entry, text_area))
    entry.focus()

    tk.Button(bottom, text="Enviar",
              command=lambda: enviar_mensaje(entry, text_area)).pack(side=tk.LEFT, padx=(5, 2))
    tk.Button(bottom, text="Transacción",
              command=lambda: abrir_dialogo_transac(text_area)).pack(side=tk.LEFT, padx=(2, 0))

    threading.Thread(target=recibir, args=(text_area,), daemon=True).start()


def hacer_login():
    global nombre_usuario
    usr = entry_usuario.get().strip()
    pwd = entry_password.get().strip()
    if not usr or not pwd:
        messagebox.showerror("Error", "Completa todos los campos.")
        return
    send_packet(client, {"type": "login", "usuario": usr, "password": pwd})
    resp = reader.recv_packet()
    if resp.get("status") == "ok":
        nombre_usuario = usr
        root.title(f"Chat — {usr}")
        mostrar_chat()
    else:
        messagebox.showerror("Error", resp.get("message", "Error desconocido."))


def hacer_registro():
    usr = entry_usuario.get().strip()
    pwd = entry_password.get().strip()
    if not usr or not pwd:
        messagebox.showerror("Error", "Completa todos los campos.")
        return
    send_packet(client, {"type": "register", "usuario": usr, "password": pwd})
    resp = reader.recv_packet()
    if resp.get("status") == "ok":
        messagebox.showinfo("Registro exitoso", resp.get("message", ""))
    else:
        messagebox.showerror("Error", resp.get("message", "Error al registrar."))


root = tk.Tk()
root.title("Chat TCP")
root.resizable(False, False)

login_frame = tk.Frame(root, padx=30, pady=30)
login_frame.pack()

tk.Label(login_frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, pady=4)
entry_usuario = tk.Entry(login_frame, width=28)
entry_usuario.grid(row=0, column=1, pady=4)

tk.Label(login_frame, text="Contraseña:").grid(row=1, column=0, sticky=tk.W, pady=4)
entry_password = tk.Entry(login_frame, show="*", width=28)
entry_password.grid(row=1, column=1, pady=4)
entry_password.bind("<Return>", lambda _e: hacer_login())

btn_frame = tk.Frame(login_frame)
btn_frame.grid(row=2, column=0, columnspan=2, pady=15)

tk.Button(btn_frame, text="Iniciar sesión", width=14, command=hacer_login).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Registrarse",    width=14, command=hacer_registro).pack(side=tk.LEFT, padx=5)

entry_usuario.focus()
root.mainloop()
