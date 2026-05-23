import json


def send_packet(conn, data):
    conn.sendall((json.dumps(data) + "\n").encode())


def send_raw(conn, text):
    conn.sendall((text + "\n").encode())


class PacketReader:
    def __init__(self, conn):
        self.conn = conn
        self.buffer = b""

    def recv_packet(self):
        while b"\n" not in self.buffer:
            chunk = self.conn.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        decoded = line.decode()
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return decoded  # trama cruda; el receptor decide cómo parsearla
