from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import User, db
from flask import jsonify, request

jwt = JWTManager()

def init_auth(app):
    jwt.init_app(app)

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'error': 'Invalid token',
        'message': 'The token provided is invalid'
    }), 401

def register_user(username, password):
    if User.query.filter_by(username=username).first():
        return False, "Username already exists"
    
    user = User(
        username=username,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    return True, "User registered successfully"

def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=username)
        return True, access_token
    return False, "Invalid credentials"
