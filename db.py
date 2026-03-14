import sqlite3

def init_db():
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()

    cursor.execute("""
        DROP TABLE IF EXISTS mensajes
    """)
    conn.commit()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            texto TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            password TEXT
        )
    """)

    conn.close()

def guardar_mensaje(usuario, texto):
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mensajes (usuario, texto) VALUES (?, ?)", (usuario, texto))
    conn.commit()
    conn.close()

def validar_usuario(usuario, password):
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND password = ?", (usuario, password))
    usuario = cursor.fetchone()
    return usuario


