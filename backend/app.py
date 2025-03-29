try:
    import requests
    import os
    import pandas as pd
    import matplotlib.pyplot as plt
    from flask import Flask, request, jsonify
    from flask_sqlalchemy import SQLAlchemy
    from flask_cors import CORS
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    print("AVISO: Instala los módulos requeridos para la funcionalidad completa.")
    print("pip install -r requeriments.txt")
    exit(1)

from datetime import datetime, timedelta
from User import User, db
from Etf import ETF

app = Flask(__name__)
CORS(app)  # Permitir solicitudes desde el frontend

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')

# Crear directorio 'instance' si no existe
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Configurar la ruta de la base de datos
db_path = os.path.join(instance_path, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)

# Configuración de las API keys para Alpha Vantage y Tiingo
# Asegúrate de reemplazar estos valores con tus propias claves
ALPHA_VANTAGE_API_KEY = ""  # Reemplaza con tu API key real
TIINGO_API_TOKEN = ""  # Reemplaza con tu token real

# URL base para las APIs
base_url_alphavantage = "https://www.alphavantage.co/query"
base_url_tiingo = "https://api.tiingo.com"

def obtener_y_almacenar_etfs():
    """
    Obtiene los ETFs disponibles de la API Tiingo y los almacena en la base de datos.
    Esta función se ejecutará al iniciar la aplicación.
    """
    print("Iniciando obtención de ETFs desde Tiingo...")
    
    # Lista de símbolos de ETFs populares para solicitar (puedes ampliarla)
    etfs_populares = [
        "SPY", "VOO", "QQQ", "VTI", "IWM", "EFA", "VWO", "GLD", 
        "VEA", "BND", "VIG", "VTV", "VUG", "VNQ", "XLF", "IEMG"
    ]
    
    etfs_guardados = 0
    etfs_actualizados = 0
    
    for simbolo in etfs_populares:
        try:
            # URL para obtener información del ETF
            url = f"{base_url_tiingo}/tiingo/daily/{simbolo}"
            
            # Parámetros de la solicitud
            params = {
                'token': TIINGO_API_TOKEN
            }
            
            # Realizar la solicitud para obtener información básica
            respuesta = requests.get(url, params=params)
            respuesta.raise_for_status()
            info_etf = respuesta.json()
            
            # Verificar si ya existe este ETF en la base de datos
            etf_existente = ETF.query.filter_by(symbol=simbolo).first()
            
            if etf_existente:
                # Actualizar la información existente
                etf_existente.name = info_etf.get('name', f"ETF {simbolo}")
                etf_existente.description = info_etf.get('description', '')
                etf_existente.last_update = datetime.now()
                etfs_actualizados += 1
            else:
                # Crear un nuevo registro
                nuevo_etf = ETF(
                    symbol=simbolo,
                    name=info_etf.get('name', f"ETF {simbolo}"),
                    description=info_etf.get('description', ''),
                    category=info_etf.get('assetType', 'ETF')
                )
                db.session.add(nuevo_etf)
                etfs_guardados += 1
            
            # Guardar cambios
            db.session.commit()
            print(f"ETF {simbolo} procesado correctamente.")
            
        except Exception as e:
            print(f"Error procesando ETF {simbolo}: {str(e)}")
            db.session.rollback()
    
    print(f"Proceso completado. ETFs nuevos: {etfs_guardados}, ETFs actualizados: {etfs_actualizados}")
    return etfs_guardados, etfs_actualizados

# Crear la base de datos (solo la primera vez)
# Crear la base de datos y actualizar datos al iniciar la aplicación
with app.app_context():
    db.create_all()
    etf_count = ETF.query.count()
    
    if etf_count == 0:
        print("No se encontraron ETFs en la base de datos. Obteniendo datos iniciales...")
        obtener_y_almacenar_etfs()
    else:
        # Verificar si necesitamos actualizar los precios (si han pasado más de 24 horas desde la última actualización)
        etf_muestra = ETF.query.first()
        ultima_actualizacion = etf_muestra.last_update if etf_muestra else None
        
        if not ultima_actualizacion or (datetime.now() - ultima_actualizacion).total_seconds() > 86400:  # 24 horas en segundos
            print(f"Actualizando precios y volúmenes de {etf_count} ETFs existentes...")
            obtener_y_almacenar_etfs()
        else:
            print(f"ETFs ya están actualizados. Última actualización: {ultima_actualizacion}")

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




def obtener_y_almacenar_etfs():
    """
    Obtiene los ETFs disponibles de la API Tiingo y los almacena en la base de datos.
    Esta función se ejecutará al iniciar la aplicación.
    """
    print("Iniciando obtención de ETFs desde Tiingo...")
    
    # Lista de símbolos de ETFs populares para solicitar (puedes ampliarla)
    etfs_populares = [
        "SPY", "VOO", "QQQ", "VTI", "IWM", "EFA", "VWO", "GLD", 
        "VEA", "BND", "VIG", "VTV", "VUG", "VNQ", "XLF", "IEMG"
    ]
    
    etfs_guardados = 0
    etfs_actualizados = 0
    
    # Fecha para obtener datos de precios (hoy)
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    # Fecha una semana atrás (para asegurar tener datos)
    fecha_inicio = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    for simbolo in etfs_populares:
        try:
            # URL para obtener información básica del ETF
            url_info = f"{base_url_tiingo}/tiingo/daily/{simbolo}"
            
            # Parámetros de la solicitud de información
            params_info = {
                'token': TIINGO_API_TOKEN
            }
            
            # Realizar la solicitud para obtener información básica
            respuesta_info = requests.get(url_info, params=params_info)
            respuesta_info.raise_for_status()
            info_etf = respuesta_info.json()
            
            # URL para obtener precios recientes
            url_precios = f"{base_url_tiingo}/tiingo/daily/{simbolo}/prices"
            
            # Parámetros para la solicitud de precios
            params_precios = {
                'startDate': fecha_inicio,
                'endDate': fecha_fin,
                'format': 'json',
                'token': TIINGO_API_TOKEN
            }
            
            # Realizar la solicitud para obtener precios
            respuesta_precios = requests.get(url_precios, params=params_precios)
            respuesta_precios.raise_for_status()
            datos_precios = respuesta_precios.json()
            
            # Obtener el precio y volumen más reciente si hay datos disponibles
            precio_actual = None
            volumen_actual = None
            fecha_precio = None
            
            if datos_precios and len(datos_precios) > 0:
                # Ordenar por fecha (más reciente primero)
                datos_precios.sort(key=lambda x: x.get('date', ''), reverse=True)
                dato_reciente = datos_precios[0]
                
                precio_actual = dato_reciente.get('close')
                volumen_actual = dato_reciente.get('volume')
                fecha_precio = datetime.strptime(dato_reciente.get('date', '')[:10], '%Y-%m-%d')
            
            # Verificar si ya existe este ETF en la base de datos
            etf_existente = ETF.query.filter_by(symbol=simbolo).first()
            
            if etf_existente:
                # Actualizar la información existente
                etf_existente.name = info_etf.get('name', f"ETF {simbolo}")
                etf_existente.description = info_etf.get('description', '')
                etf_existente.category = info_etf.get('assetType', 'ETF')
                
                # Actualizar precio y volumen
                etf_existente.current_price = precio_actual
                etf_existente.current_volume = volumen_actual
                etf_existente.price_date = fecha_precio
                
                etf_existente.last_update = datetime.now()
                etfs_actualizados += 1
                
                print(f"ETF {simbolo} actualizado con precio: {precio_actual}, volumen: {volumen_actual}")
            else:
                # Crear un nuevo registro
                nuevo_etf = ETF(
                    symbol=simbolo,
                    name=info_etf.get('name', f"ETF {simbolo}"),
                    description=info_etf.get('description', ''),
                    category=info_etf.get('assetType', 'ETF'),
                    current_price=precio_actual,
                    current_volume=volumen_actual,
                    price_date=fecha_precio
                )
                db.session.add(nuevo_etf)
                etfs_guardados += 1
                
                print(f"Nuevo ETF {simbolo} añadido con precio: {precio_actual}, volumen: {volumen_actual}")
            
            # Guardar cambios
            db.session.commit()
            print(f"ETF {simbolo} procesado correctamente.")
            
        except Exception as e:
            print(f"Error procesando ETF {simbolo}: {str(e)}")
            db.session.rollback()
    
    print(f"Proceso completado. ETFs nuevos: {etfs_guardados}, ETFs actualizados: {etfs_actualizados}")
    return etfs_guardados, etfs_actualizados

# Ruta para forzar la actualización de ETFs manualmente
@app.route('/api/admin/actualizar-etfs', methods=['POST'])
def actualizar_etfs_endpoint():
    nuevos, actualizados = obtener_y_almacenar_etfs()
    return jsonify({
        "mensaje": "Actualización de ETFs completada",
        "nuevos": nuevos,
        "actualizados": actualizados
    }), 200
    
@app.route('/api/etfs', methods=['GET'])
def listar_etfs():
    etfs = ETF.query.all()
    resultado = [etf.to_dict() for etf in etfs]
    return jsonify({"etfs": resultado}), 200



@app.route('/api/etf/<string:simbolo>', methods=['GET'])
def obtener_etf(simbolo):
    """
    Obtiene información detallada de un ETF, incluyendo precio y volumen actuales.
    """
    # Verificar si el ETF existe en la base de datos
    etf = ETF.query.filter_by(symbol=simbolo).first()
    
    if not etf:
        return jsonify({"error": f"ETF con símbolo {simbolo} no encontrado"}), 404
    
    return jsonify(etf.to_dict()), 200

@app.route('/api/etf/<string:simbolo>/precios', methods=['GET'])
def obtener_precios_etf(simbolo):
    """
    Obtiene el historial de precios recientes de un ETF específico.
    """
    # Verificar si el ETF existe en la base de datos
    etf = ETF.query.filter_by(symbol=simbolo).first()
    
    if not etf:
        return jsonify({"error": f"ETF con símbolo {simbolo} no encontrado"}), 404
    
    # Obtener parámetros opcionales de la solicitud
    dias = request.args.get('dias', default=30, type=int)
    
    # Fechas para la solicitud
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
    
    try:
        # URL para obtener precios
        url = f"{base_url_tiingo}/tiingo/daily/{simbolo}/prices"
        
        # Parámetros para la solicitud
        params = {
            'startDate': fecha_inicio,
            'endDate': fecha_fin,
            'format': 'json',
            'token': TIINGO_API_TOKEN
        }
        
        # Realizar la solicitud
        respuesta = requests.get(url, params=params)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # Formatear los datos para el frontend
        historico = []
        for dato in datos:
            historico.append({
                'fecha': dato.get('date'),
                'apertura': dato.get('open'),
                'maximo': dato.get('high'),
                'minimo': dato.get('low'),
                'cierre': dato.get('close'),
                'volumen': dato.get('volume')
            })
        
        # Calcular estadísticas si hay datos
        estadisticas = {}
        if historico:
            precios_cierre = [item['cierre'] for item in historico if item['cierre']]
            volumenes = [item['volumen'] for item in historico if item['volumen']]
            
            estadisticas = {
                'precio_promedio': sum(precios_cierre) / len(precios_cierre) if precios_cierre else None,
                'precio_max': max(precios_cierre) if precios_cierre else None,
                'precio_min': min(precios_cierre) if precios_cierre else None,
                'volumen_promedio': sum(volumenes) / len(volumenes) if volumenes else None
            }
        
        return jsonify({
            'etf': etf.to_dict(),
            'historico': historico,
            'estadisticas': estadisticas
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error al obtener precios: {str(e)}"}), 500



# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True)