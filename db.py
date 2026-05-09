import sqlite3
import hashlib


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    with sqlite3.connect("chat.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT,
                texto TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.commit()


def crear_usuario(usuario, password):
    with sqlite3.connect("chat.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
            (usuario, _hash_password(password))
        )
        conn.commit()


def guardar_mensaje(usuario, texto):
    with sqlite3.connect("chat.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO mensajes (usuario, texto) VALUES (?, ?)",
            (usuario, texto)
        )
        conn.commit()


def validar_usuario(usuario, password):
    with sqlite3.connect("chat.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND password = ?",
            (usuario, _hash_password(password))
        )
        return cursor.fetchone()
