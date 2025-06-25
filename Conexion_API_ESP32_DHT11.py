"""
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// Pines y tipo de sensor
#define DHTPIN 14        // Pin conectado al DHT11
#define DHTTYPE DHT11    // Tipo de sensor

// Credenciales WiFi
const char* ssid = "NombreDeTuRedWiFi";
const char* password = "TuContraseñaWiFi";

// URL del servidor Flask
const char* serverName = "http://Ip del Pc donde esta la API:5000/api/sensor";

// Instancias
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();

  // Conectar al WiFi
  WiFi.begin(ssid, password);
  Serial.print("Conectando al WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.println("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Leer temperatura y humedad
  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();

  // Verifica si la lectura es válida
  if (isnan(temperatura) || isnan(humedad)) {
    Serial.println("Error leyendo del DHT11");
    delay(5000);
    return;
  }

  // Imprimir valores
  Serial.print("Temperatura: ");
  Serial.print(temperatura);
  Serial.print(" °C, Humedad: ");
  Serial.print(humedad);
  Serial.println(" %");

  // Enviar datos si está conectado al WiFi
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    // Crear JSON
    String json = "{\"temperatura\": " + String(temperatura, 1) + ", \"humedad\": " + String(humedad, 1) + "}";

    // Enviar POST
    int httpResponseCode = http.POST(json);

    // Ver resultado
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Respuesta del servidor: " + response);
    } else {
      Serial.print("Error al enviar POST: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi desconectado");
  }

  delay(3000); // Esperar 3 segundos antes del próximo envío
}

"""

from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
from flask import render_template

# pip install flask pymongo python-dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
timezone = pytz.timezone('America/Bogota')

# Conexión a MongoDB
uri = os.getenv("MongoDB_URI")
client = MongoClient(uri)
db = client["InformacionSensores"]
coleccion = db["ESP32DHT11"]

@app.route('/')
def inicio():
    return render_template("dashboard.html")

@app.route('/api/sensor', methods=['POST'])
def recibir_datos():
    try:
        data = request.get_json(force=True)
        print("Datos recibidos:", data)
        data["timestamp"] = datetime.now(timezone)
        coleccion.insert_one(data)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 400

@app.route('/api/datos', methods=['GET'])
def obtener_datos():
    try:
        datos = list(coleccion.find().sort("timestamp", -1).limit(50))
        for dato in datos:
            dato["_id"] = str(dato["_id"])
            dato["timestamp"] = dato["timestamp"].astimezone(timezone).isoformat()        
        return jsonify(datos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
