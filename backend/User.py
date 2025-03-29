from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name= db.Column(db.String(100), nullable=True)
    risk_profile= db.Column(db.String(100), nullable=True)
    creation_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'risk_profile': self.risk_profile,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None
        }