from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from User import db, User

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, default=0.0)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Establecer relación con el usuario
    user = db.relationship('User', backref=db.backref('portfolios', lazy=True))
    
    def __init__(self, user_id, name, value=0.0):
        self.user_id = user_id
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f'<Portfolio {self.name} de usuario {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'value': self.value,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }