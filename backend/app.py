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
    print(" Para instalarlo, crea un entorno virtual y ejecuta este comando en la carpeta raiz del proyecto:\npip install -r requeriments.txt")
    exit(1)

from datetime import datetime, timedelta
from User import User, db
from Etf import ETF
from Portfolio import Portfolio
from Portfolio_item import Portfolio_item

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5501"]}}) # Permitir solicitudes desde el frontend

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
# Obtener desde variables de entorno o usar valores predeterminados
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
TIINGO_API_TOKEN = os.environ.get("TIINGO_API_TOKEN", "")

# URL base para las APIs
base_url_alphavantage = "https://www.alphavantage.co/query"
base_url_tiingo = "https://api.tiingo.com"

def obtener_y_almacenar_etfs(actualizar_todos=False):
    """
    Obtiene los ETFs disponibles de la API Tiingo y los almacena en la base de datos.
    
    Args:
        actualizar_todos (bool): Si es True, actualiza todos los ETFs aunque estén recientes.
                                 Si es False, solo actualiza los ETFs sin datos de precio recientes.
    
    Returns:
        tuple: (etfs_nuevos, etfs_actualizados) Cantidad de ETFs nuevos y actualizados.
    """
    print("Iniciando obtención de ETFs desde Tiingo...")
    
    # Lista de símbolos de ETFs populares para solicitar
    etfs_populares = [
        "SPY", "VOO", "QQQ", "VTI", "IWM", "EFA", "VWO", "GLD", 
        "VEA", "BND", "VIG", "VTV", "VUG", "VNQ", "XLF", "IEMG",
        "AGG", "IJR", "IJH", "LQD", "TLT", "SCHD", "VCIT", "VCSH"
    ]
    
    stats = {"nuevos": 0, "actualizados": 0, "errores": 0}
    
    # Fechas para la solicitud de precios
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    fecha_inicio = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    for simbolo in etfs_populares:
        try:
            # Verificar si el ETF ya existe en la base de datos
            etf_existente = ETF.query.filter_by(symbol=simbolo).first()
            
            # Si el ETF existe y tiene precios recientes, podemos omitir la actualización
            if not actualizar_todos and etf_existente and etf_existente.price_date:
                dias_desde_actualizacion = (datetime.now() - etf_existente.price_date).days
                if dias_desde_actualizacion < 1:  # Si se actualizó hoy, omitir
                    print(f"Omitiendo ETF {simbolo} - ya está actualizado (hace {dias_desde_actualizacion} días)")
                    continue
            
            # Obtener info básica y precios del ETF
            info_etf, precio_actual, volumen_actual, fecha_precio = _obtener_datos_etf(
                simbolo, 
                fecha_inicio, 
                fecha_fin
            )
            
            if etf_existente:
                # Actualizar ETF existente
                _actualizar_etf_existente(
                    etf_existente, 
                    info_etf, 
                    precio_actual, 
                    volumen_actual, 
                    fecha_precio
                )
                stats["actualizados"] += 1
                print(f"ETF {simbolo} actualizado con precio: {precio_actual}, volumen: {volumen_actual}")
            else:
                # Crear nuevo ETF
                nuevo_etf = _crear_nuevo_etf(
                    simbolo, 
                    info_etf, 
                    precio_actual, 
                    volumen_actual, 
                    fecha_precio
                )
                db.session.add(nuevo_etf)
                stats["nuevos"] += 1
                print(f"Nuevo ETF {simbolo} añadido con precio: {precio_actual}, volumen: {volumen_actual}")
            
            # Guardar cambios
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            stats["errores"] += 1
            print(f"Error procesando ETF {simbolo}: {str(e)}")
    
    print(f"Proceso completado. ETFs nuevos: {stats['nuevos']}, actualizados: {stats['actualizados']}, errores: {stats['errores']}")
    return stats["nuevos"], stats["actualizados"]


def _obtener_datos_etf(simbolo, fecha_inicio, fecha_fin):
    """
    Función auxiliar para obtener información y precios de un ETF.
    
    Args:
        simbolo (str): Símbolo del ETF.
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD.
        
    Returns:
        tuple: (info_etf, precio_actual, volumen_actual, fecha_precio)
    """
    # 1. Obtener información básica del ETF
    url_info = f"{base_url_tiingo}/tiingo/daily/{simbolo}"
    params_info = {'token': TIINGO_API_TOKEN}
    
    respuesta_info = requests.get(url_info, params_info)
    respuesta_info.raise_for_status()
    info_etf = respuesta_info.json()
    
    # 2. Obtener precios recientes
    url_precios = f"{base_url_tiingo}/tiingo/daily/{simbolo}/prices"
    params_precios = {
        'startDate': fecha_inicio,
        'endDate': fecha_fin,
        'format': 'json',
        'token': TIINGO_API_TOKEN
    }
    
    respuesta_precios = requests.get(url_precios, params_precios)
    respuesta_precios.raise_for_status()
    datos_precios = respuesta_precios.json()
    
    # 3. Extraer precio y volumen más recientes
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
    
    return info_etf, precio_actual, volumen_actual, fecha_precio


def _actualizar_etf_existente(etf, info_etf, precio_actual, volumen_actual, fecha_precio):
    """
    Actualiza un ETF existente con nueva información.
    
    Args:
        etf (ETF): Objeto ETF existente.
        info_etf (dict): Información básica del ETF.
        precio_actual (float): Precio de cierre más reciente.
        volumen_actual (int): Volumen más reciente.
        fecha_precio (datetime): Fecha del precio más reciente.
    """
    etf.name = info_etf.get('name', f"ETF {etf.symbol}")
    etf.description = info_etf.get('description', '')
    etf.category = info_etf.get('assetType', 'ETF')
    
    # Actualizar precio y volumen solo si hay datos nuevos
    if precio_actual is not None:
        etf.current_price = precio_actual
    if volumen_actual is not None:
        etf.current_volume = volumen_actual
    if fecha_precio is not None:
        etf.price_date = fecha_precio
    
    etf.last_update = datetime.now()


def _crear_nuevo_etf(simbolo, info_etf, precio_actual, volumen_actual, fecha_precio):
    """
    Crea un nuevo objeto ETF.
    
    Args:
        simbolo (str): Símbolo del ETF.
        info_etf (dict): Información básica del ETF.
        precio_actual (float): Precio de cierre más reciente.
        volumen_actual (int): Volumen más reciente.
        fecha_precio (datetime): Fecha del precio más reciente.
        
    Returns:
        ETF: Nuevo objeto ETF.
    """
    return ETF(
        symbol=simbolo,
        name=info_etf.get('name', f"ETF {simbolo}"),
        description=info_etf.get('description', ''),
        category=info_etf.get('assetType', 'ETF'),
        current_price=precio_actual,
        current_volume=volumen_actual,
        price_date=fecha_precio
    )

# Crear la base de datos (solo la primera vez)
# Crear la base de datos y actualizar datos al iniciar la aplicación
with app.app_context():
    db.create_all()
    etf_count = ETF.query.count()
    
    if etf_count == 0:
        print("No se encontraron ETFs en la base de datos. Obteniendo datos iniciales...")
        obtener_y_almacenar_etfs()
    else:
        # Verificar si necesitamos actualizar algún ETF sin precios o con precios antiguos
        etfs_sin_precios = ETF.query.filter(ETF.current_price.is_(None)).count()
        etfs_antiguos = ETF.query.filter(ETF.price_date < (datetime.now() - timedelta(days=1))).count()
        
        if etfs_sin_precios > 0 or etfs_antiguos > 0:
            print(f"Actualizando ETFs: {etfs_sin_precios} sin precios, {etfs_antiguos} con precios antiguos...")
            obtener_y_almacenar_etfs()
        else:
            print(f"Todos los {etf_count} ETFs tienen precios actualizados.")

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

# Ruta para forzar la actualización de ETFs manualmente
@app.route('/api/admin/actualizar-etfs', methods=['POST'])
def actualizar_etfs_endpoint():
    """
    Fuerza la actualización de todos los ETFs, incluso los que tienen datos recientes.
    """
    try:
        nuevos, actualizados = obtener_y_almacenar_etfs(actualizar_todos=True)
        return jsonify({
            "mensaje": "Actualización de ETFs completada con éxito",
            "nuevos": nuevos,
            "actualizados": actualizados
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Error en la actualización de ETFs: {str(e)}"
        }), 500

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

@app.route('/api/comprar-etf', methods=['POST'])
def comprar_etf():
    """
    Registra la compra de un ETF por parte de un usuario.
    Actualiza o crea una cartera para el usuario según sea necesario.
    """
    # Verificar autenticación
    data = request.get_json()
    username = data.get('username')
    simbolo_etf = data.get('simbolo')
    monto = data.get('monto')
    cantidad = data.get('cantidad')
    
    if not username or not simbolo_etf or not monto or not cantidad:
        return jsonify({"error": "Faltan datos obligatorios"}), 400
    
    try:
        # 1. Verificar que el usuario existe
        usuario = User.query.filter_by(username=username).first()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # 2. Verificar que el ETF existe
        etf = ETF.query.filter_by(symbol=simbolo_etf).first()
        if not etf:
            return jsonify({"error": f"ETF {simbolo_etf} no encontrado"}), 404
        
        # 3. Buscar o crear la cartera del usuario
        cartera = Portfolio.query.filter_by(user_id=usuario.id, name="Principal").first()
        if not cartera:
            # Crear una cartera principal si no existe
            cartera = Portfolio(
                user_id=usuario.id,
                name="Principal",
                value=0.0
            )
            db.session.add(cartera)
            db.session.flush()  # Obtener ID sin hacer commit
        
        # 4. Buscar si ya tiene este ETF en su cartera
        item_existente = Portfolio_item.query.filter_by(
            portfolio_id=cartera.id, 
            etf_id=etf.id
        ).first()
        
        if item_existente:
            # Actualizar item existente (compra adicional)
            nueva_cantidad = item_existente.allocation + cantidad
            item_existente.allocation = nueva_cantidad
        else:
            # Crear nuevo item en la cartera
            nuevo_item = Portfolio_item(
                portfolio_id=cartera.id,
                etf_id=etf.id,
                allocation=cantidad
            )
            db.session.add(nuevo_item)
        
        # 5. Actualizar el valor de la cartera
        cartera.value += monto
        cartera.last_update = datetime.now()
        
        # 6. Guardar cambios en la base de datos
        db.session.commit()
        
        return jsonify({
            "mensaje": f"Compra de {cantidad} unidades de {simbolo_etf} registrada correctamente",
            "cartera": cartera.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al procesar la compra: {str(e)}"}), 500

# Añadamos también un endpoint para obtener la cartera de un usuario
@app.route('/api/cartera/<string:username>', methods=['GET'])
def obtener_cartera(username):
    """
    Obtiene la cartera de inversiones de un usuario específico.
    """
    try:
        # Buscar al usuario
        usuario = User.query.filter_by(username=username).first()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Buscar la cartera principal
        cartera = Portfolio.query.filter_by(user_id=usuario.id, name="Principal").first()
        if not cartera:
            # Si no tiene cartera, devolver una vacía
            return jsonify({
                "usuario": username,
                "cartera": {
                    "valor_total": 0,
                    "items": []
                }
            }), 200
        
        # Obtener los items de la cartera con detalles
        items_cartera = []
        for item in Portfolio_item.query.filter_by(portfolio_id=cartera.id).all():
            etf = ETF.query.get(item.etf_id)
            if etf:
                valor_actual = item.allocation * etf.current_price if etf.current_price else 0
                items_cartera.append({
                    "simbolo": etf.symbol,
                    "nombre": etf.name,
                    "cantidad": item.allocation,
                    "precio_actual": etf.current_price,
                    "valor_total": valor_actual
                })
        
        return jsonify({
            "usuario": username,
            "cartera": {
                "id": cartera.id,
                "nombre": cartera.name,
                "valor_total": cartera.value,
                "ultima_actualizacion": cartera.last_update.isoformat(),
                "items": items_cartera
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error al obtener la cartera: {str(e)}"}), 500

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True)