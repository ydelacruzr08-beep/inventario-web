from flask import Flask, render_template, request, redirect, url_for, send_file
import csv
import os
import glob
from openpyxl import Workbook
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)

# ======================================================
# 🔹 CONFIGURACIÓN GENERAL
# ======================================================
BASE = os.path.dirname(os.path.abspath(__file__))
KITS = os.path.join(BASE, "kits.csv")
MOV = os.path.join(BASE, "movimientos.csv")

# ======================================================
# 🔹 CONEXIÓN A BASE DE DATOS (RENDER)
# 🔹 NO TOCAR – SOLO VERIFICA QUE DATABASE_URL EXISTA
# ======================================================
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("❌ DATABASE_URL no está configurada en Render")

    result = urlparse(db_url)

    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode="require"
    )

# ======================================================
# 🔹 TEST DE SERVIDOR + BASE DE DATOS
# 👉 https://TU_APP.onrender.com/test-db
# ======================================================
@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        return "✅ Servidor activo y DB conectada correctamente"
    except Exception as e:
        return f"❌ Error de conexión: {e}", 500

# ======================================================
# ================== INVENTARIOS ======================
# ======================================================
def ordenar_piezas(pieza):
    return (0, int(pieza)) if pieza.isdigit() else (1, pieza)

def leer_inventario(ruta):
    datos = {}
    with open(ruta, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            datos[r["Numero de pieza"]] = {
                "nombre": r["Nombre"],
                "cantidad": int(r["Cantidad"])
            }
    return dict(sorted(datos.items(), key=lambda x: ordenar_piezas(x[0])))

def guardar_inventario(datos, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Numero de pieza", "Nombre", "Cantidad", "Estado"])
        for p, d in datos.items():
            estado = "SIN STOCK" if d["cantidad"] <= 0 else "OK"
            w.writerow([p, d["nombre"], d["cantidad"], estado])

# ======================================================
# ================== MENÚ ==============================
# ======================================================
@app.route("/")
def menu():
    return render_template("menu.html")

# ======================================================
# ================== INVENTARIOS ======================
# ======================================================
@app.route("/inventarios")
def seleccionar_inventario():
    archivos = [
        os.path.basename(x)
        for x in glob.glob(os.path.join(BASE, "inventario*.csv"))
    ]
    return render_template("seleccionar.html", archivos=archivos)

@app.route("/inventarios/crear", methods=["POST"])
def crear_inventario():
    nombre = request.form["nombre"].strip()
    if not nombre:
        return redirect("/inventarios")

    ruta = os.path.join(BASE, f"inventario_{nombre}.csv")
    if not os.path.exists(ruta):
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["Numero de pieza", "Nombre", "Cantidad", "Estado"]
            )
    return redirect("/inventarios")

@app.route("/inventario/<archivo>")
def inventario(archivo):
    ruta = os.path.join(BASE, archivo)
    if not os.path.exists(ruta):
        return "Inventario no encontrado"
    datos = leer_inventario(ruta)
    return render_template("inventario.html", datos=datos, archivo=archivo)

@app.route("/inventario/editar", methods=["POST"])
def editar_inventario():
    archivo = request.form["archivo"]
    pieza = request.form["pieza"]
    nombre = request.form["nombre"]
    cantidad = int(request.form["cantidad"])

    ruta = os.path.join(BASE, archivo)
    datos = leer_inventario(ruta)
    datos[pieza] = {"nombre": nombre, "cantidad": cantidad}
    guardar_inventario(datos, ruta)

    return redirect(url_for("inventario", archivo=archivo))

@app.route("/inventario/eliminar", methods=["POST"])
def eliminar_pieza():
    archivo = request.form["archivo"]
    pieza = request.form["pieza"]

    ruta = os.path.join(BASE, archivo)
    datos = leer_inventario(ruta)
    if pieza in datos:
        del datos[pieza]

    guardar_inventario(datos, ruta)
    return redirect(url_for("inventario", archivo=archivo))

@app.route("/inventario/descargar/<archivo>")
def descargar_excel(archivo):
    ruta = os.path.join(BASE, archivo)
    if not os.path.exists(ruta):
        return "No encontrado", 404

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"

    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.reader(f):
            ws.append(fila)

    salida = ruta.replace(".csv", ".xlsx")
    wb.save(salida)
    return send_file(salida, as_attachment=True)

# ======================================================
# ================== MOVIMIENTOS ======================
# ======================================================
def registrar_movimiento(empleado, inventario, pieza, cantidad, accion):
    existe = os.path.exists(MOV)
    with open(MOV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not existe:
            w.writerow(["Fecha", "Empleado", "Inventario", "Pieza", "Cantidad", "Accion"])
        w.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            empleado,
            inventario,
            pieza,
            cantidad,
            accion
        ])

@app.route("/movimientos")
def movimientos():
    datos = []
    if os.path.exists(MOV):
        with open(MOV, newline="", encoding="utf-8") as f:
            datos = list(csv.reader(f))[1:]

    inventarios = [
        os.path.basename(x)
        for x in glob.glob(os.path.join(BASE, "inventario*.csv"))
    ]

    return render_template("movimientos.html", datos=datos, inventarios=inventarios)

@app.route("/movimientos/registrar", methods=["POST"])
def registrar_salida():
    empleado = request.form["empleado"]
    archivo = request.form["inventario"]
    pieza = request.form["pieza"]
    cantidad = int(request.form["cantidad"])

    ruta = os.path.join(BASE, archivo)
    datos = leer_inventario(ruta)

    if pieza not in datos:
        return "Pieza no encontrada", 400
    if datos[pieza]["cantidad"] < cantidad:
        return "Stock insuficiente", 400

    datos[pieza]["cantidad"] -= cantidad
    guardar_inventario(datos, ruta)
    registrar_movimiento(empleado, archivo, pieza, cantidad, "SALIDA")

    return redirect("/movimientos")

# ======================================================
# ================== MAIN ==============================
# ⚠️ Render ignora esto y usa gunicorn
# ======================================================
if __name__ == "__main__":
    app.run(debug=True)
