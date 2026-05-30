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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                total REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                nombre_producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                FOREIGN KEY (venta_id) REFERENCES ventas(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
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


def agregar_producto(nombre, precio, stock=0):
    with sqlite3.connect("chat.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
            (nombre, float(precio), int(stock))
        )
        conn.commit()
        return cursor.lastrowid


def obtener_productos():
    with sqlite3.connect("chat.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, precio, stock FROM productos ORDER BY nombre")
        return [dict(row) for row in cursor.fetchall()]


def registrar_venta(usuario, items):
    """items: list of {"producto_id": int, "cantidad": int}"""
    with sqlite3.connect("chat.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        total = 0.0
        detalle = []
        for item in items:
            pid = item["producto_id"]
            qty = int(item["cantidad"])
            cursor.execute(
                "SELECT id, nombre, precio, stock FROM productos WHERE id = ?", (pid,)
            )
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Producto ID {pid} no encontrado.")
            if prod["stock"] < qty:
                raise ValueError(
                    f"Stock insuficiente para '{prod['nombre']}' (disponible: {prod['stock']})."
                )
            subtotal = prod["precio"] * qty
            total += subtotal
            detalle.append({
                "producto_id": pid,
                "nombre": prod["nombre"],
                "cantidad": qty,
                "precio_unitario": prod["precio"],
                "subtotal": round(subtotal, 2),
            })
        cursor.execute(
            "INSERT INTO ventas (usuario, total) VALUES (?, ?)",
            (usuario, round(total, 2))
        )
        venta_id = cursor.lastrowid
        for d in detalle:
            cursor.execute(
                "INSERT INTO detalle_ventas "
                "(venta_id, producto_id, nombre_producto, cantidad, precio_unitario) "
                "VALUES (?, ?, ?, ?, ?)",
                (venta_id, d["producto_id"], d["nombre"], d["cantidad"], d["precio_unitario"])
            )
            cursor.execute(
                "UPDATE productos SET stock = stock - ? WHERE id = ?",
                (d["cantidad"], d["producto_id"])
            )
        conn.commit()
        return venta_id, round(total, 2), detalle


def obtener_ventas():
    with sqlite3.connect("chat.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id, v.usuario, v.total, v.timestamp,
                   GROUP_CONCAT(dv.nombre_producto || ' x' || dv.cantidad, ', ') AS items
            FROM ventas v
            LEFT JOIN detalle_ventas dv ON v.id = dv.venta_id
            GROUP BY v.id
            ORDER BY v.timestamp DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
