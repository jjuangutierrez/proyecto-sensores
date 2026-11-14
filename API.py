from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app)

try:
    cliente = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    cliente.admin.command('ping')
    db = cliente["monitoreo_industrial"]
    sensores_col = db["sensores"]
    print("Conectado exitosamente a MongoDB (monitoreo_industrial.sensores)")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")

def validar_datos_sensor(data):
    campos_requeridos = ["tipo", "valor", "ubicacion", "fecha"]
    for campo in campos_requeridos:
        if campo not in data or data[campo] is None or data[campo] == "":
            return f"El campo obligatorio '{campo}' no fue proporcionado o está vacío."

    tipo = str(data.get("tipo")).lower().strip()
    valor = data.get("valor")
    fecha = str(data.get("fecha")).strip()

    tipos_permitidos = ["temperatura", "presion", "vibracion"]
    if tipo not in tipos_permitidos:
        return f"Tipo inválido. Los permitidos son: {tipos_permitidos}."

    try:
        valor = float(valor)
    except (ValueError, TypeError):
        return "El campo 'valor' debe ser un número válido."

    if tipo == "temperatura" and not (-10 <= valor <= 100):
        return "La temperatura debe estar en el rango de -10°C a 100°C."
    elif tipo == "presion" and not (0 <= valor <= 500):
        return "La presión debe estar en el rango de 0 a 500 kPa."
    elif tipo == "vibracion" and not (0 <= valor <= 5):
        return "La vibración debe estar en el rango de 0 a 5 mm/s."

    try:
        datetime.fromisoformat(fecha)
    except ValueError:
        return "La fecha no tiene un formato válido (ejemplo: 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS')."

    return None

@app.route("/sensores", methods=["POST"])
def agregar_sensor():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se enviaron datos en formato JSON."}), 400

    error = validar_datos_sensor(data)
    if error:
        return jsonify({"error": error}), 400

    nuevo_sensor = {
        "tipo": str(data["tipo"]).lower().strip(),
        "valor": float(data["valor"]),
        "ubicacion": str(data["ubicacion"]).strip(),
        "fecha": str(data["fecha"]).strip()
    }

    try:
        resultado = sensores_col.insert_one(nuevo_sensor)
        nuevo_sensor["_id"] = str(resultado.inserted_id)

        return jsonify({
            "mensaje": "Sensor registrado exitosamente",
            "sensor": nuevo_sensor
        }), 201
    except PyMongoError as e:
        return jsonify({"error": f"Fallo en la base de datos: {str(e)}"}), 500


@app.route("/sensores", methods=["GET"])
def obtener_todos_los_sensores():
    try:
        sensores = list(sensores_col.find({}, {"_id": 0}))
        return jsonify(sensores), 200
    except PyMongoError as e:
        return jsonify({"error": f"Fallo al consultar la base de datos: {str(e)}"}), 500


@app.route("/sensores/<string:tipo>", methods=["GET"])
def obtener_sensores_por_tipo(tipo):
    tipo_normalizado = tipo.lower().strip()
    try:
        sensores = list(sensores_col.find({"tipo": tipo_normalizado}, {"_id": 0}))
        if not sensores:
            return jsonify({"mensaje": f"No se encontraron sensores de tipo '{tipo_normalizado}'."}), 404
        return jsonify(sensores), 200
    except PyMongoError as e:
        return jsonify({"error": f"Fallo al consultar la base de datos: {str(e)}"}), 500


@app.route("/sensores/<string:tipo>", methods=["PUT"])
def actualizar_sensor_por_tipo(tipo):
    tipo_normalizado = tipo.lower().strip()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se enviaron datos en formato JSON para actualizar."}), 400

    data["tipo"] = tipo_normalizado
    error = validar_datos_sensor(data)
    if error:
        return jsonify({"error": error}), 400

    datos_actualizados = {
        "tipo": tipo_normalizado,
        "valor": float(data["valor"]),
        "ubicacion": str(data["ubicacion"]).strip(),
        "fecha": str(data["fecha"]).strip()
    }

    try:
        resultado = sensores_col.update_one(
            {"tipo": tipo_normalizado},
            {"$set": datos_actualizados}
        )
        if resultado.matched_count == 0:
            return jsonify({"error": f"No se encontró ningún sensor de tipo '{tipo_normalizado}' para actualizar."}), 404

        return jsonify({
            "mensaje": f"Sensor de tipo '{tipo_normalizado}' actualizado con éxito.",
            "sensor": datos_actualizados
        }), 200
    except PyMongoError as e:
        return jsonify({"error": f"Fallo al actualizar en la base de datos: {str(e)}"}), 500

@app.route("/sensores/<string:tipo>", methods=["DELETE"])
def eliminar_sensor_por_tipo(tipo):
    tipo_normalizado = tipo.lower().strip()
    try:
        resultado = sensores_col.delete_one({"tipo": tipo_normalizado})
        if resultado.deleted_count == 0:
            return jsonify({"error": f"No se encontró ningún sensor de tipo '{tipo_normalizado}' para eliminar."}), 404

        return jsonify({"mensaje": f"Sensor de tipo '{tipo_normalizado}' eliminado con éxito."}), 200
    except PyMongoError as e:
        return jsonify({"error": f"Fallo al eliminar en la base de datos: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)