import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import main as servidor
import db


def _append_log(log_area, line):
    log_area.config(state=tk.NORMAL)
    log_area.insert(tk.END, line + "\n")
    log_area.yview(tk.END)
    log_area.config(state=tk.DISABLED)


def _update_clients(listbox, clients_frame, snapshot):
    listbox.delete(0, tk.END)
    for _, usr in snapshot:
        listbox.insert(tk.END, usr)
    clients_frame.config(text=f"Clientes conectados: {len(snapshot)}")


def _refresh_products(listbox):
    listbox.delete(0, tk.END)
    for p in db.obtener_productos():
        listbox.insert(tk.END,
            f"[{p['id']:>3}]  {p['nombre']:<20}  ${p['precio']:>7.2f}   stock: {p['stock']}")


def abrir_ventas():
    win = tk.Toplevel()
    win.title("Historial de Ventas")
    win.minsize(680, 400)

    tree = ttk.Treeview(
        win,
        columns=("id", "usuario", "total", "timestamp", "items"),
        show="headings",
    )
    for col, text, width in [
        ("id",        "#",          40),
        ("usuario",   "Usuario",   100),
        ("total",     "Total",      80),
        ("timestamp", "Fecha/Hora",150),
        ("items",     "Productos", 290),
    ]:
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor=tk.W)

    sb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
    sb.pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=(0, 10))

    for v in db.obtener_ventas():
        tree.insert("", tk.END, values=(
            v["id"], v["usuario"], f"${v['total']:.2f}",
            v["timestamp"], v["items"] or "—",
        ))

    tk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0, 10))


def build_gui():
    root = tk.Tk()
    root.title("Super Mercado R — Puerto 5000")
    root.minsize(540, 640)

    # ── Clients panel ──────────────────────────────────────────────
    clients_frame = tk.LabelFrame(root, text="Clientes conectados: 0", padx=5, pady=5)
    clients_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

    clients_listbox = tk.Listbox(clients_frame, height=4, selectmode=tk.BROWSE)
    clients_listbox.pack(fill=tk.X)

    # ── Log panel ──────────────────────────────────────────────────
    log_frame = tk.LabelFrame(root, text="Log del servidor", padx=5, pady=5)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 0))

    log_area = scrolledtext.ScrolledText(
        log_frame, wrap=tk.WORD, state=tk.DISABLED, width=65, height=10,
        font=("Courier", 10)
    )
    log_area.pack(fill=tk.BOTH, expand=True)

    # ── Send-to-all panel ──────────────────────────────────────────
    send_frame = tk.LabelFrame(root, text="Enviar mensaje a todos los clientes", padx=5, pady=5)
    send_frame.pack(fill=tk.X, padx=10, pady=(8, 0))

    msg_entry = tk.Entry(send_frame, font=("TkDefaultFont", 11))
    msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

    def send_message():
        msg = msg_entry.get().strip()
        if msg:
            servidor.send_server_message(msg)
            msg_entry.delete(0, tk.END)

    msg_entry.bind("<Return>", lambda _e: send_message())
    tk.Button(send_frame, text="Enviar", width=10, command=send_message).pack(side=tk.LEFT)

    # ── Products panel ─────────────────────────────────────────────
    prod_frame = tk.LabelFrame(root, text="Gestión de Productos", padx=5, pady=5)
    prod_frame.pack(fill=tk.X, padx=10, pady=(8, 10))

    input_row = tk.Frame(prod_frame)
    input_row.pack(fill=tk.X, pady=(0, 4))

    tk.Label(input_row, text="Nombre:").pack(side=tk.LEFT)
    e_nombre = tk.Entry(input_row, width=14)
    e_nombre.pack(side=tk.LEFT, padx=(2, 8))

    tk.Label(input_row, text="Precio:").pack(side=tk.LEFT)
    e_precio = tk.Entry(input_row, width=7)
    e_precio.pack(side=tk.LEFT, padx=(2, 8))

    tk.Label(input_row, text="Stock:").pack(side=tk.LEFT)
    e_stock = tk.Entry(input_row, width=6)
    e_stock.pack(side=tk.LEFT, padx=(2, 8))

    prod_listbox = tk.Listbox(prod_frame, height=6, font=("Courier", 9))
    prod_listbox.pack(fill=tk.X, pady=(0, 4))

    def agregar_producto():
        nombre = e_nombre.get().strip()
        precio_txt = e_precio.get().strip()
        stock_txt = e_stock.get().strip() or "0"
        if not nombre or not precio_txt:
            messagebox.showerror("Error", "Nombre y precio son obligatorios.")
            return
        try:
            precio = float(precio_txt)
            stock = int(stock_txt)
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser número decimal y stock entero.")
            return
        try:
            db.agregar_producto(nombre, precio, stock)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        servidor._log(f"Producto agregado: {nombre} (${precio:.2f}, stock: {stock})")
        e_nombre.delete(0, tk.END)
        e_precio.delete(0, tk.END)
        e_stock.delete(0, tk.END)
        e_nombre.focus()
        _refresh_products(prod_listbox)

    e_stock.bind("<Return>", lambda _e: agregar_producto())
    tk.Button(input_row, text="Agregar", width=9, command=agregar_producto).pack(side=tk.LEFT)

    btn_row = tk.Frame(prod_frame)
    btn_row.pack(fill=tk.X)
    tk.Button(btn_row, text="Actualizar lista", width=14,
              command=lambda: _refresh_products(prod_listbox)).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(btn_row, text="Ver Ventas", width=12,
              command=abrir_ventas).pack(side=tk.LEFT)

    # ── Wire callbacks ─────────────────────────────────────────────
    def on_log(line):
        root.after(0, _append_log, log_area, line)

    def on_clients(snapshot):
        root.after(0, _update_clients, clients_listbox, clients_frame, snapshot)

    def on_error(msg):
        root.after(0, messagebox.showerror, "Error al iniciar el servidor", msg)

    servidor.set_callbacks(log_cb=on_log, clients_cb=on_clients, error_cb=on_error)

    # ── Start server thread ────────────────────────────────────────
    threading.Thread(target=servidor.iniciar_servidor, daemon=True).start()

    # Cargar lista de productos al arrancar
    root.after(500, _refresh_products, prod_listbox)

    root.mainloop()


if __name__ == "__main__":
    build_gui()
