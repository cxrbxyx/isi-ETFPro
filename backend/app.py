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
CORS(app, resources={r"/api/*": {"origins": ["*"]}}) # Permitir solicitudes desde el frontend

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

# Configuración de las API keys para Tiingo y Twelve Data
# Obtener desde variables de entorno o usar valores predeterminados
TIINGO_API_TOKEN = os.environ.get("TIINGO_API_TOKEN", "")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")

# URL base para las APIs
base_url_alphavantage = "https://www.alphavantage.co/query"
base_url_tiingo = "https://api.tiingo.com"
base_url_twelve_data = "https://api.twelvedata.com"

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
    Intenta primero con Tiingo y, si falla, usa Twelve Data como respaldo.
    
    Args:
        simbolo (str): Símbolo del ETF.
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD.
        
    Returns:
        tuple: (info_etf, precio_actual, volumen_actual, fecha_precio)
    """
    try:
        return _obtener_datos_tiingo(simbolo, fecha_inicio, fecha_fin)
    except Exception as e:
        print(f"Error al obtener datos de Tiingo para {simbolo}: {str(e)}. Intentando con Twelve Data...")
        return _obtener_datos_twelve_data(simbolo, fecha_inicio, fecha_fin)


def _obtener_datos_tiingo(simbolo, fecha_inicio, fecha_fin):
    """
    Obtiene información y precios de un ETF desde la API Tiingo.
    
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


def _obtener_datos_twelve_data(simbolo, fecha_inicio, fecha_fin):
    """
    Obtiene información y precios de un ETF desde la API Twelve Data.
    
    Args:
        simbolo (str): Símbolo del ETF.
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD.
        
    Returns:
        tuple: (info_etf, precio_actual, volumen_actual, fecha_precio)
    """
    # 1. Obtener información detallada del ETF
    url_info = f"{base_url_twelve_data}/etf"
    params_info = {
        'symbol': simbolo,
        'apikey': TWELVE_DATA_API_KEY
    }
    
    try:
        # Primer intento: obtener información específica de ETF
        respuesta_info = requests.get(url_info, params_info)
        respuesta_info.raise_for_status()
        info_etf_raw = respuesta_info.json()
        
        # Verificar si tenemos la información que necesitamos
        if 'name' not in info_etf_raw:
            raise ValueError("Información de ETF incompleta")
            
    except Exception as e:
        # Si falla, intentar obtener información del símbolo genérico
        print(f"Error al obtener información específica de ETF: {str(e)}. Intentando con symbol details...")
        
        url_symbol_info = f"{base_url_twelve_data}/symbol_search"
        params_symbol_info = {
            'symbol': simbolo,
            'outputsize': 1,  # Solo necesitamos el primer resultado
            'apikey': TWELVE_DATA_API_KEY
        }
        
        respuesta_symbol = requests.get(url_symbol_info, params_symbol_info)
        respuesta_symbol.raise_for_status()
        symbol_data = respuesta_symbol.json()
        
        # Extraer información del primer resultado si existe
        if 'data' in symbol_data and len(symbol_data['data']) > 0:
            info_etf_raw = {
                'name': symbol_data['data'][0].get('instrument_name', f"ETF {simbolo}"),
                'description': symbol_data['data'][0].get('description', ''),
                'exchange': symbol_data['data'][0].get('exchange', '')
            }
        else:
            # Si tampoco hay información básica, usar valores por defecto
            info_etf_raw = {
                'name': f"ETF {simbolo}",
                'description': f"Información no disponible para {simbolo}",
                'exchange': ''
            }
    
    # Crear diccionario con formato compatible con Tiingo para unificar respuesta
    info_etf = {
        'name': info_etf_raw.get('name', f"ETF {simbolo}"),
        'description': info_etf_raw.get('description', ''),
        'assetType': 'ETF',
        'exchange': info_etf_raw.get('exchange', '')
    }
    
    # 2. Obtener precios recientes
    url_precios = f"{base_url_twelve_data}/time_series"
    params_precios = {
        'symbol': simbolo,
        'interval': '1day',
        'outputsize': '30',  # Obtener 30 días de datos
        'apikey': TWELVE_DATA_API_KEY
    }
    
    respuesta_precios = requests.get(url_precios, params_precios)
    respuesta_precios.raise_for_status()
    datos_precios_raw = respuesta_precios.json()
    
    # 3. Extraer precio y volumen más recientes
    precio_actual = None
    volumen_actual = None
    fecha_precio = None
    
    if 'values' in datos_precios_raw and len(datos_precios_raw['values']) > 0:
        dato_reciente = datos_precios_raw['values'][0]  # El más reciente está primero
        
        precio_actual = float(dato_reciente.get('close', 0))
        volumen_actual = float(dato_reciente.get('volume', 0)) if dato_reciente.get('volume') else 0
        fecha_precio = datetime.strptime(dato_reciente.get('datetime', '')[:10], '%Y-%m-%d')
    
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


def _obtener_precios_tiingo(simbolo, fecha_inicio, fecha_fin):
    """
    Obtiene el historial de precios desde Tiingo.
    
    Args:
        simbolo (str): Símbolo del ETF.
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD.
        
    Returns:
        list: Lista de diccionarios con los datos históricos.
    """
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
        
    return historico


def _obtener_precios_twelve_data(simbolo, fecha_inicio, fecha_fin):
    """
    Obtiene el historial de precios desde Twelve Data.
    
    Args:
        simbolo (str): Símbolo del ETF.
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD.
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD.
        
    Returns:
        list: Lista de diccionarios con los datos históricos.
    """
    # Calcular cantidad de días entre inicio y fin
    date_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
    date_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d')
    dias = (date_fin_obj - date_inicio_obj).days + 1
    outputsize = min(5000, max(30, dias))  # 30 mínimo, 5000 máximo según API
    
    # URL para obtener precios
    url = f"{base_url_twelve_data}/time_series"
    
    # Parámetros para la solicitud
    params = {
        'symbol': simbolo,
        'interval': '1day',
        'outputsize': outputsize,
        'apikey': TWELVE_DATA_API_KEY
    }
    
    # Realizar la solicitud
    respuesta = requests.get(url, params=params)
    respuesta.raise_for_status()
    datos = respuesta.json()
    
    # Formatear los datos para el frontend
    historico = []
    if 'values' in datos:
        for dato in datos['values']:
            fecha = dato.get('datetime')
            # Verificar si la fecha está dentro del rango solicitado
            if fecha >= fecha_inicio and fecha <= fecha_fin:
                historico.append({
                    'fecha': fecha,
                    'apertura': float(dato.get('open')),
                    'maximo': float(dato.get('high')),
                    'minimo': float(dato.get('low')),
                    'cierre': float(dato.get('close')),
                    'volumen': float(dato.get('volume')) if dato.get('volume') else None
                })
    
    return historico


def recalcular_valor_cartera(cartera_id):
    """
    Recalcula el valor de una cartera basado en los precios actuales de los ETFs.
    
    Args:
        cartera_id (int): ID de la cartera a recalcular
        
    Returns:
        float: Valor total calculado
    """
    valor_total = 0
    
    for item in Portfolio_item.query.filter_by(portfolio_id=cartera_id).all():
        etf = ETF.query.get(item.etf_id)
        if etf and etf.current_price:
            valor_total += item.allocation * etf.current_price
    
    # Actualizar el valor en la base de datos
    cartera = Portfolio.query.get(cartera_id)
    if cartera:
        cartera.value = valor_total
        cartera.last_update = datetime.now()
        db.session.commit()
    
    return valor_total


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
    Intenta primero con Tiingo y, si falla, usa Twelve Data como respaldo.
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
        # Intentar primero con Tiingo
        historico = _obtener_precios_tiingo(simbolo, fecha_inicio, fecha_fin)
    except Exception as e:
        print(f"Error al obtener precios de Tiingo para {simbolo}: {str(e)}. Intentando con Twelve Data...")
        try:
            # Si falla, intentar con Twelve Data
            historico = _obtener_precios_twelve_data(simbolo, fecha_inicio, fecha_fin)
        except Exception as e:
            return jsonify({"error": f"Error al obtener precios: {str(e)}"}), 500
    
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

@app.route('/api/comprar-etf', methods=['POST'])
def comprar_etf():
    """
    Registra la compra de un ETF por parte de un usuario.
    Actualiza o crea una cartera para el usuario según sea necesario.
    El valor de la cartera se calculará basado en los precios actuales.
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
            nueva_cantidad = item_existente.allocation + float(cantidad)
            item_existente.allocation = nueva_cantidad
        else:
            # Crear nuevo item en la cartera
            nuevo_item = Portfolio_item(
                portfolio_id=cartera.id,
                etf_id=etf.id,
                allocation=float(cantidad)
            )
            db.session.add(nuevo_item)
        
        # 5. Recalcular el valor total de la cartera en base a las posesiones actuales
        valor_total = recalcular_valor_cartera(cartera.id)
        
        # Actualizar el valor de la cartera con el cálculo basado en los activos
        cartera.value = valor_total
        cartera.last_update = datetime.now()
        
        # 6. Guardar los cambios
        db.session.commit()
        
        return jsonify({
            "mensaje": f"Compra de {cantidad} unidades de {simbolo_etf} registrada correctamente",
            "cartera": {
                "id": cartera.id,
                "nombre": cartera.name,
                "valor_total": cartera.value,
                "ultima_actualizacion": cartera.last_update.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al procesar la compra: {str(e)}"}), 500

# Añadamos también un endpoint para obtener la cartera de un usuario
@app.route('/api/cartera/<string:username>', methods=['GET'])
def obtener_cartera(username):
    """
    Obtiene la cartera de inversiones de un usuario específico.
    Calcula el valor total basado en los precios actuales de los ETFs.
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
        valor_total_calculado = recalcular_valor_cartera(cartera.id)
        
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
                "valor_total": valor_total_calculado,
                "ultima_actualizacion": cartera.last_update.isoformat(),
                "items": items_cartera
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error al obtener la cartera: {str(e)}"}), 500

@app.route('/api/cartera/<string:username>/actualizar', methods=['POST'])
def actualizar_valor_cartera(username):
    """
    Actualiza el valor de la cartera de un usuario según los precios actuales de los ETFs.
    """
    try:
        # Buscar al usuario
        usuario = User.query.filter_by(username=username).first()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Buscar la cartera principal
        cartera = Portfolio.query.filter_by(user_id=usuario.id, name="Principal").first()
        if not cartera:
            return jsonify({"error": "El usuario no tiene una cartera"}), 404
        
        # Recalcular el valor
        nuevo_valor = recalcular_valor_cartera(cartera.id)
        
        return jsonify({
            "mensaje": "Valor de la cartera actualizado correctamente",
            "valor_anterior": cartera.value,
            "valor_nuevo": nuevo_valor
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error al actualizar el valor de la cartera: {str(e)}"}), 500

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True)