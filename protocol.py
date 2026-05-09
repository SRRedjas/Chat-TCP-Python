import json


def send_packet(conn, data):
    msg = json.dumps(data) + "\n"
    conn.sendall(msg.encode())


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
        return json.loads(line.decode())
