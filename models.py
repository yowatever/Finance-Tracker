from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import TypeDecorator, Numeric

db = SQLAlchemy()

class SqliteDecimal(TypeDecorator):
    impl = Numeric
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return float(value)
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return Decimal(str(value))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    amount = db.Column(SqliteDecimal(10, 2), nullable=False)
    memo = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'type': self.type,
            'amount': float(self.amount),
            'memo': self.memo
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    transactions = db.relationship('Transaction', backref='user', lazy=True)
