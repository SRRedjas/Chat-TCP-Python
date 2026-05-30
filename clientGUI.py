import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from protocol import send_packet, send_raw, PacketReader


client = None
reader = None
nombre_usuario = None

_sale_dialog_callback = None   # recibe la lista de productos para abrir el diálogo
_pending_sale_callback = None  # recibe el resultado de una venta en curso


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
    global _sale_dialog_callback, _pending_sale_callback
    while True:
        try:
            packet = reader.recv_packet()
            if packet is None:
                break
            if isinstance(packet, str):
                root.after(0, _append_text, text_area, packet)
                continue

            ptype = packet.get("type")

            if ptype == "products_list":
                cb = _sale_dialog_callback
                _sale_dialog_callback = None
                if cb:
                    root.after(0, cb, packet.get("products", []))

            elif ptype == "sale_result":
                cb = _pending_sale_callback
                _pending_sale_callback = None
                if cb:
                    root.after(0, cb, packet)

            elif ptype == "sale_broadcast":
                usr = packet.get("usuario", "?")
                vid = packet.get("venta_id", "?")
                total = packet.get("total", 0)
                root.after(
                    0, _append_text, text_area,
                    f"[VENTA] {usr} registró venta #{vid} — Total: ${total:.2f}"
                )

            elif ptype == "message":
                msg = f"{packet['usuario']}: {packet['texto']}"
                root.after(0, _append_text, text_area, msg)

            elif ptype == "transac":
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


def abrir_dialogo_venta(text_area, products):
    if not products:
        messagebox.showinfo("Sin productos", "No hay productos cargados en el servidor.")
        return

    win = tk.Toplevel(root)
    win.title("Nueva Venta")
    win.resizable(False, False)
    win.grab_set()

    # Cabecera de columnas
    hdr = tk.Frame(win, bg="#e0e0e0")
    hdr.pack(fill=tk.X, padx=12, pady=(10, 0))
    for col, (text, w, anchor) in enumerate([
        ("Producto", 22, tk.W), ("Precio", 8, tk.E), ("Stock", 6, tk.E), ("Cant.", 6, tk.CENTER)
    ]):
        tk.Label(hdr, text=text, width=w, anchor=anchor, bg="#e0e0e0",
                 font=("TkDefaultFont", 9, "bold")).grid(row=0, column=col, padx=2)

    # Filas de productos
    list_frame = tk.Frame(win)
    list_frame.pack(fill=tk.X, padx=12, pady=4)

    spins = {}  # producto_id -> (StringVar, producto_dict)
    total_var = tk.StringVar(value="Total: $0.00")

    def actualizar_total(*_):
        total = sum(
            (int(var.get()) if var.get().isdigit() else 0) * prod["precio"]
            for var, prod in spins.values()
        )
        total_var.set(f"Total: ${total:.2f}")

    for i, prod in enumerate(products):
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        row_frame = tk.Frame(list_frame, bg=bg)
        row_frame.pack(fill=tk.X)
        tk.Label(row_frame, text=prod["nombre"], width=22, anchor=tk.W, bg=bg).grid(
            row=0, column=0, padx=2, pady=2)
        tk.Label(row_frame, text=f"${prod['precio']:.2f}", width=8, anchor=tk.E, bg=bg).grid(
            row=0, column=1, padx=2)
        tk.Label(row_frame, text=str(prod["stock"]), width=6, anchor=tk.E, bg=bg).grid(
            row=0, column=2, padx=2)
        var = tk.StringVar(value="0")
        var.trace_add("write", actualizar_total)
        sb = tk.Spinbox(row_frame, from_=0, to=max(prod["stock"], 0), width=5,
                        textvariable=var, state=tk.NORMAL if prod["stock"] > 0 else tk.DISABLED)
        sb.grid(row=0, column=3, padx=(4, 2), pady=2)
        spins[prod["id"]] = (var, prod)

    # Total
    tk.Label(win, textvariable=total_var, font=("TkDefaultFont", 11, "bold")).pack(pady=(8, 4))

    # Botones
    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=(4, 14))

    def enviar_venta():
        global _pending_sale_callback
        items = [
            {"producto_id": pid, "cantidad": int(var.get())}
            for pid, (var, _) in spins.items()
            if var.get().isdigit() and int(var.get()) > 0
        ]
        if not items:
            messagebox.showerror("Error", "Selecciona al menos un producto.", parent=win)
            return

        def on_result(packet):
            if packet.get("status") == "ok":
                vid = packet.get("venta_id")
                total = packet.get("total", 0)
                detalle = packet.get("detalle", [])
                lineas = [f"Venta #{vid} registrada\nTotal: ${total:.2f}\n"]
                lineas += [f"  {d['nombre']} x{d['cantidad']} = ${d['subtotal']:.2f}"
                           for d in detalle]
                messagebox.showinfo("Venta exitosa", "\n".join(lineas))
                _append_text(text_area, f"[VENTA] Tu venta #{vid} fue registrada — ${total:.2f}")
            else:
                messagebox.showerror("Error en venta", packet.get("message", "Error desconocido."))

        _pending_sale_callback = on_result
        send_packet(client, {"type": "sale", "items": items})
        win.destroy()

    tk.Button(btn_frame, text="Registrar Venta", width=16, command=enviar_venta).pack(
        side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Cancelar", width=12, command=win.destroy).pack(
        side=tk.LEFT, padx=6)

    win.bind("<Return>", lambda _e: enviar_venta())


def solicitar_venta(text_area):
    """Pide la lista de productos al servidor y abre el diálogo de venta."""
    global _sale_dialog_callback
    if not client:
        return
    _sale_dialog_callback = lambda products: abrir_dialogo_venta(text_area, products)
    send_packet(client, {"type": "get_products"})


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
              command=lambda: abrir_dialogo_transac(text_area)).pack(side=tk.LEFT, padx=(2, 2))
    tk.Button(bottom, text="Venta",
              command=lambda: solicitar_venta(text_area),
              bg="#2e7d32", fg="white", activebackground="#1b5e20", activeforeground="white",
              ).pack(side=tk.LEFT, padx=(2, 0))

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
        root.title(f"Supermercado — {usr}")
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


def conectar_directo():
    global nombre_usuario
    nombre_usuario = "Invitado"
    root.title("Supermercado — Invitado")
    mostrar_chat()


def conectar():
    global client, reader
    ip = entry_ip.get().strip() or "localhost"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, 5000))
        client = sock
        reader = PacketReader(client)
        connect_frame.pack_forget()
        login_frame.pack()
        entry_usuario.focus()
    except OSError as e:
        messagebox.showerror("Error de conexión", f"No se pudo conectar a {ip}:5000\n{e}")


root = tk.Tk()
root.title("Supermercado TCP")
root.resizable(False, False)

# --- Pantalla de conexión ---
connect_frame = tk.Frame(root, padx=30, pady=30)
connect_frame.pack()

tk.Label(connect_frame, text="IP del servidor:").grid(row=0, column=0, sticky=tk.W, pady=4)
entry_ip = tk.Entry(connect_frame, width=28)
entry_ip.insert(0, "localhost")
entry_ip.grid(row=0, column=1, pady=4)
entry_ip.bind("<Return>", lambda _e: conectar())

tk.Button(connect_frame, text="Conectar", width=14, command=conectar).grid(
    row=1, column=0, columnspan=2, pady=15
)

# --- Pantalla de login (oculta hasta conectar) ---
login_frame = tk.Frame(root, padx=30, pady=30)

tk.Label(login_frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, pady=4)
entry_usuario = tk.Entry(login_frame, width=28)
entry_usuario.grid(row=0, column=1, pady=4)

tk.Label(login_frame, text="Contraseña:").grid(row=1, column=0, sticky=tk.W, pady=4)
entry_password = tk.Entry(login_frame, show="*", width=28)
entry_password.grid(row=1, column=1, pady=4)
entry_password.bind("<Return>", lambda _e: hacer_login())

btn_frame = tk.Frame(login_frame)
btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 5))

tk.Button(btn_frame, text="Iniciar sesión", width=14, command=hacer_login).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Registrarse",    width=14, command=hacer_registro).pack(side=tk.LEFT, padx=5)

tk.Frame(login_frame, height=1, bg="gray").grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
tk.Button(
    login_frame, text="Acceso directo (sin login)",
    width=30, fg="gray", command=conectar_directo
).grid(row=4, column=0, columnspan=2, pady=(0, 10))

root.mainloop()
