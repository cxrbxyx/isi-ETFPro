from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from User import db

class ETF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    assets = db.Column(db.Float, default=0.0)
    
    # Nuevos campos para precio y volumen
    current_price = db.Column(db.Float, nullable=True)
    current_volume = db.Column(db.Float, nullable=True)
    price_date = db.Column(db.DateTime, nullable=True)
    
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, symbol, name, description=None, category=None, assets=0.0,
                 current_price=None, current_volume=None, price_date=None):
        self.symbol = symbol
        self.name = name
        self.description = description
        self.category = category
        self.assets = assets
        self.current_price = current_price
        self.current_volume = current_volume
        self.price_date = price_date
    
    def __repr__(self):
        return f'<ETF {self.symbol}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'assets': self.assets,
            'current_price': self.current_price,
            'current_volume': self.current_volume,
            'price_date': self.price_date.isoformat() if self.price_date else None,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }