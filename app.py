from flask import Flask, render_template, request, redirect, url_for
import csv
import json
import os

def maintenance_mode():
    try:
        with open("maintenance.txt", "r") as f:
            return f.read().strip() == "ON"
    except:
        return False

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(BASE, "inventario.csv")
ESTADO = os.path.join(BASE, "estado.json")

def sistema_activo():
    with open(ESTADO, "r") as f:
        estado = json.load(f)
    return estado["activo"]

@app.route("/")
def index():
    if not sistema_activo():
        return "Sistema pausado por el administrador"

    inventario = []
    with open(INV, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            inventario.append(row)

    return "<h1>Inventario funcionando</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


