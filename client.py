import socket
import threading
import sys


if len(sys.argv) > 1:
    server = sys.argv[1]
    print('se proporciono servidor:' + sys.argv[1])
else:
    server = "localhost"



def recibir(client):
    while True:
        try:
            msg = client.recv(1024).decode()
            if msg:
                print(msg)
        except:
            break

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server, 5000))

threading.Thread(target=recibir, args=(client,)).start()

while True:
    msg = input("")
    client.sendall(msg.encode())
