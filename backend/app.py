from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

import requests, json, jsonify
from datetime import datetime, timedelta

from User import User, db

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    PANDAS_INSTALLED = True
except ImportError:
    PANDAS_INSTALLED = False
    print("AVISO: pandas y/o matplotlib no están instalados.")
    print("Para visualización y análisis de datos avanzados, instálalos con:")
    print("pip install pandas matplotlib")
    print("Continuando con funcionalidad básica...\n")

app = Flask(__name__)
CORS(app)  # Permitir solicitudes desde el frontend

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)

# Configuración de las API keys para Alpha Vantage y Tiingo
# Asegúrate de reemplazar estos valores con tus propias claves
ALPHA_VANTAGE_API_KEY = ""  # Reemplaza con tu API key real
TIINGO_API_TOKEN = ""  # Reemplaza con tu token real

# URL base para las APIs
base_url_alphavantage = "https://www.alphavantage.co/query"
base_url_tiingo = "https://api.tiingo.com"

# Crear la base de datos (solo la primera vez)
with app.app_context():
    db.create_all()

# Ruta para registrar un nuevo usuario
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    # Verificar si el usuario ya existe
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "El usuario ya existe"}), 400

    # Crear un nuevo usuario con método de hash predeterminado (no especificamos method)
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Usuario registrado exitosamente"}), 201

# Ruta para iniciar sesión
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    # Buscar al usuario en la base de datos
    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    return jsonify({"message": "Inicio de sesión exitoso", "user": {"username": user.username}}), 200

@app.route('/api/etf/historico', methods=['GET'])
def obtener_historico_etf():
    # Obtener el símbolo del ETF de los parámetros de la consulta
    simbolo = request.args.get('simbolo')
    
    if not simbolo:
        return jsonify({"error": "Se requiere un símbolo de ETF"}), 400
    
    # Calcular fechas (última semana)
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    fecha_inicio = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Crear URL para la solicitud
    url = f"{base_url_tiingo}/tiingo/daily/{simbolo}/prices"
    
    # Parámetros de la solicitud
    params = {
        'startDate': fecha_inicio,
        'endDate': fecha_fin,
        'format': 'json',
        'token': TIINGO_API_TOKEN
    }
    
    # Realizar la solicitud
    try:
        respuesta = requests.get(url, params=params)
        respuesta.raise_for_status()  # Lanzar excepciones para códigos de error HTTP
        datos = respuesta.json()
        
        if not datos:
            return jsonify({"error": f"No se encontraron datos para el ETF: {simbolo}"}), 404
        
        # Si pandas está instalado, podemos hacer análisis adicional
        if PANDAS_INSTALLED:
            df = pd.DataFrame(datos)
            
            # Calcular estadísticas básicas
            estadisticas = {
                "precio_promedio": float(df['close'].mean()),
                "precio_maximo": float(df['high'].max()),
                "precio_minimo": float(df['low'].min()),
                "volumen_promedio": float(df['volume'].mean()) if 'volume' in df else None
            }
            
            return jsonify({
                "datos": datos,
                "estadisticas": estadisticas,
                "mensaje": "Datos obtenidos exitosamente"
            }), 200
        
        return jsonify({
            "datos": datos,
            "mensaje": "Datos obtenidos exitosamente"
        }), 200
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Error en la API de Tiingo: {str(e)}"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error de conexión: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500




# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True)