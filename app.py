from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secreto"

# -------------------------
# CONEXIÓN A BASE DE DATOS
# -------------------------
def conectar():
    return sqlite3.connect("database.db")

# -------------------------
# CREAR TABLAS
# -------------------------
with conectar() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        password TEXT,
        rol TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS registros(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        fecha TEXT,
        entrada TEXT,
        salida TEXT,
        horas REAL
    )
    """)

# -------------------------
# LOGIN
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"]
        password = request.form["password"]

        with conectar() as conn:
            user = conn.execute(
                "SELECT * FROM usuarios WHERE nombre=? AND password=?",
                (nombre, password)
            ).fetchone()

        if user:
            session["id"] = user[0]
            session["nombre"] = user[1]
            session["rol"] = user[3]
            return redirect("/dashboard")

    return render_template("login.html")

# -------------------------
# REGISTRO
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        password = request.form["password"]
        rol = request.form["rol"]

        with conectar() as conn:
            existe = conn.execute(
                "SELECT * FROM usuarios WHERE nombre=?",
                (nombre,)
            ).fetchone()

            if existe:
                return "Ese nombre de usuario ya existe."

            conn.execute(
                "INSERT INTO usuarios(nombre,password,rol) VALUES(?,?,?)",
                (nombre, password, rol)
            )

        return redirect("/")

    return render_template("register.html")
# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "id" not in session:
        return redirect("/")

    with conectar() as conn:

        if session["rol"] == "supervisor":
            registros = conn.execute("""
                SELECT registros.id, usuarios.nombre, fecha, entrada, salida, horas
                FROM registros
                JOIN usuarios ON registros.usuario_id = usuarios.id
                ORDER BY fecha DESC
            """).fetchall()
        else:
            registros = conn.execute("""
                SELECT id, fecha, entrada, salida, horas
                FROM registros
                WHERE usuario_id=?
                ORDER BY fecha DESC
            """, (session["id"],)).fetchall()

    return render_template("dashboard.html", registros=registros)

# -------------------------
# MARCAR ENTRADA / SALIDA
# -------------------------
@app.route("/marcar/<tipo>")
def marcar(tipo):
    if "id" not in session:
        return redirect("/")

    usuario_id = session["id"]
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M:%S")

    with conectar() as conn:
        registro_hoy = conn.execute("""
            SELECT id, entrada, salida FROM registros
            WHERE usuario_id=? AND fecha=?
        """, (usuario_id, fecha_hoy)).fetchone()

        if tipo == "Entrada":

            if registro_hoy and registro_hoy[1] is not None:
                return "Ya marcaste entrada hoy."

            conn.execute("""
                INSERT INTO registros(usuario_id, fecha, entrada, salida, horas)
                VALUES(?,?,?,?,?)
            """, (usuario_id, fecha_hoy, hora_actual, None, 0))

        elif tipo == "Salida":

            if not registro_hoy or registro_hoy[1] is None:
                return "Primero debes marcar entrada."

            if registro_hoy[2] is not None:
                return "Ya marcaste salida hoy."

            entrada_time = datetime.strptime(
                fecha_hoy + " " + registro_hoy[1],
                "%Y-%m-%d %H:%M:%S"
            )

            diferencia = (ahora - entrada_time).total_seconds() / 3600

            conn.execute("""
                UPDATE registros
                SET salida=?, horas=?
                WHERE id=?
            """, (hora_actual, round(diferencia,2), registro_hoy[0]))

    return redirect("/dashboard")

# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/editar/<int:id>", methods=["GET","POST"])
def editar(id):
    if "id" not in session or session["rol"] != "supervisor":
        return redirect("/")

    with conectar() as conn:

        if request.method == "POST":
            entrada = request.form["entrada"]
            salida = request.form["salida"]

            horas = 0
            if entrada and salida:
                fecha = conn.execute(
                    "SELECT fecha FROM registros WHERE id=?",
                    (id,)
                ).fetchone()[0]

                entrada_time = datetime.strptime(
                    fecha + " " + entrada,
                    "%Y-%m-%d %H:%M:%S"
                )

                salida_time = datetime.strptime(
                    fecha + " " + salida,
                    "%Y-%m-%d %H:%M:%S"
                )

                horas = (salida_time - entrada_time).total_seconds() / 3600

            conn.execute("""
                UPDATE registros
                SET entrada=?, salida=?, horas=?
                WHERE id=?
            """, (entrada, salida, round(horas,2), id))

            return redirect("/dashboard")

        registro = conn.execute(
            "SELECT fecha, entrada, salida FROM registros WHERE id=?",
            (id,)
        ).fetchone()

    return render_template("editar.html", registro=registro, id=id)

@app.route("/eliminar/<int:id>")
def eliminar(id):
    if "id" not in session or session["rol"] != "supervisor":
        return redirect("/")

    with conectar() as conn:
        conn.execute("DELETE FROM registros WHERE id=?", (id,))

    return redirect("/dashboard")



if __name__ == "__main__":
    app.run(debug=True)