from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from User import db
from Portfolio import Portfolio
from Etf import ETF

class Portfolio_item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    etf_id = db.Column(db.Integer, db.ForeignKey('etf.id'), nullable=False)
    allocation = db.Column(db.Float, nullable=False, default=0.0)  # Porcentaje de asignación en la cartera
    
    # Establecer relaciones
    portfolio = db.relationship('Portfolio', backref=db.backref('items', lazy=True))
    etf = db.relationship('ETF', backref=db.backref('portfolio_items', lazy=True))
    
    def __init__(self, portfolio_id, etf_id, allocation=0.0):
        self.portfolio_id = portfolio_id
        self.etf_id = etf_id
        self.allocation = allocation
    
    def __repr__(self):
        return f'<Portfolio_item {self.id}: ETF {self.etf_id} en Portfolio {self.portfolio_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'etf_id': self.etf_id,
            'etf_symbol': self.etf.symbol if self.etf else None,
            'allocation': self.allocation
        }