from flask import Flask, render_template
import csv
import json
import os

app = Flask(__name__)

# ================== RUTAS ==================
BASE = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(BASE, "inventario.csv")
ESTADO = os.path.join(BASE, "estado.json")
MAINTENANCE = os.path.join(BASE, "maintenance.txt")

# ================== CONTROL SISTEMA ==================
def sistema_activo():
    try:
        with open(ESTADO, "r", encoding="utf-8") as f:
            estado = json.load(f)
        return estado.get("activo", True)
    except:
        return True

def maintenance_mode():
    try:
        with open(MAINTENANCE, "r", encoding="utf-8") as f:
            return f.read().strip() == "ON"
    except:
        return False

# ================== RUTAS ==================
@app.route("/")
def index():
    if not sistema_activo():
        return "🛑 Sistema pausado por el administrador"

    return """
    <h1>Inventario funcionando al chingaso 🔥</h1>
    <a href="/inventario">Ver inventario</a>
    """

@app.route("/inventario")
def inventario():
    if maintenance_mode():
        return "🛑 Sistema en mantenimiento"

    datos = []

    if not os.path.exists(INV):
        return "❌ No existe inventario.csv"

    with open(INV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            datos.append(fila)

    return render_template("inventario.html", datos=datos)

# ================== MAIN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
