from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)  # Permitir solicitudes desde el frontend

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

# Modelo de Usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

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

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True)