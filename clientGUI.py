import socket
import threading
import sys
import tkinter as tk
from tkinter import scrolledtext

if len(sys.argv) > 1:
    server = sys.argv[1]
    print('Se proporcionó servidor:' + sys.argv[1])
else:
    server = "localhost"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server, 5000))


def recibir(client, text_area):
    while True:
        try:
            msg = client.recv(1024).decode()
            if msg:
                text_area.config(state=tk.NORMAL)
                text_area.insert(tk.END, msg + "\n")
                text_area.yview(tk.END)
                text_area.config(state=tk.DISABLED)
        except:
            break

def enviar(entry, text_area):
    msg = entry.get()
    if msg:
        client.sendall(msg.encode())
        text_area.config(state=tk.NORMAL)
        text_area.insert(tk.END, msg + "\n")
        text_area.yview(tk.END)
        text_area.config(state=tk.DISABLED)
        entry.delete(0, tk.END)

root = tk.Tk()
root.title("Cliente de Chat")

text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, width=50, height=20)
text_area.pack(padx=10, pady=10)

entry = tk.Entry(root, width=40)
entry.pack(side=tk.LEFT, padx=10, pady=10)

send_button = tk.Button(root, text="Enviar", command=lambda: enviar(entry, text_area))
send_button.pack(side=tk.LEFT, padx=5, pady=10)

threading.Thread(target=recibir, args=(client, text_area), daemon=True).start()

root.mainloop()
