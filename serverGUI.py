import tkinter as tk
from tkinter import scrolledtext
import threading
import main as servidor


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


def build_gui():
    root = tk.Tk()
    root.title("Servidor Chat TCP — Puerto 5000")
    root.minsize(520, 500)

    # ── Clients panel ──────────────────────────────────────────────
    clients_frame = tk.LabelFrame(root, text="Clientes conectados: 0", padx=5, pady=5)
    clients_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

    clients_listbox = tk.Listbox(clients_frame, height=4, selectmode=tk.BROWSE)
    clients_listbox.pack(fill=tk.X)

    # ── Log panel ──────────────────────────────────────────────────
    log_frame = tk.LabelFrame(root, text="Log del servidor", padx=5, pady=5)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 0))

    log_area = scrolledtext.ScrolledText(
        log_frame, wrap=tk.WORD, state=tk.DISABLED, width=65, height=20,
        font=("Courier", 10)
    )
    log_area.pack(fill=tk.BOTH, expand=True)

    # ── Send-to-all panel ──────────────────────────────────────────
    send_frame = tk.LabelFrame(root, text="Enviar mensaje a todos los clientes", padx=5, pady=5)
    send_frame.pack(fill=tk.X, padx=10, pady=10)

    msg_entry = tk.Entry(send_frame, font=("TkDefaultFont", 11))
    msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

    def send_message():
        msg = msg_entry.get().strip()
        if msg:
            servidor.send_server_message(msg)
            msg_entry.delete(0, tk.END)

    msg_entry.bind("<Return>", lambda _e: send_message())
    tk.Button(send_frame, text="Enviar", width=10, command=send_message).pack(side=tk.LEFT)

    # ── Wire callbacks ─────────────────────────────────────────────
    def on_log(line):
        root.after(0, _append_log, log_area, line)

    def on_clients(snapshot):
        root.after(0, _update_clients, clients_listbox, clients_frame, snapshot)

    servidor.set_callbacks(log_cb=on_log, clients_cb=on_clients)

    # ── Start server thread ────────────────────────────────────────
    threading.Thread(target=servidor.iniciar_servidor, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    build_gui()
