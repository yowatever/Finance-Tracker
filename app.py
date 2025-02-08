from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import csv
from io import StringIO
import logging
from logging.handlers import RotatingFileHandler
from models import db, Transaction, User
from config import Config
from auth import init_auth, jwt_required, get_jwt_identity, register_user, authenticate_user
from validators import validate_transaction, ValidationError

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
init_auth(app)

# Setup rate limiting
limiter = Limiter(
    key_func=get_remote_address, 
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Setup logging
if not app.debug:
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'errors': e.args[0]}), 400

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
    
    success, message = register_user(data['username'], data['password'])
    if success:
        return jsonify({'message': message}), 201
    return jsonify({'error': message}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
    
    success, result = authenticate_user(data['username'], data['password'])
    if success:
        return jsonify({'access_token': result}), 200
    return jsonify({'error': result}), 401

@app.route('/transactions', methods=['POST'])
@jwt_required()
@limiter.limit(Config.UPLOAD_RATE_LIMIT)
def upload_transactions():
    if 'data' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['data']
    if not file:
        return jsonify({'error': 'Empty file'}), 400

    user_id = User.query.filter_by(username=get_jwt_identity()).first().id
    content = file.read().decode('utf-8')
    csv_reader = csv.reader(StringIO(content))
    
    transactions_added = 0
    errors = []
    
    for line_num, line in enumerate(csv_reader, 1):
        # Skip empty lines and comments
        if not line or line[0].startswith('#'):
            continue
            
        try:
            if len(line) != 4:
                errors.append(f"Line {line_num}: Invalid number of fields")
                continue
                
            date, trans_type, amount, memo = [x.strip() for x in line]
            
            # Validate and parse the transaction
            date, trans_type, amount, memo = validate_transaction(date, trans_type, amount, memo)
            
            transaction = Transaction(
                date=date,
                type=trans_type,
                amount=amount,
                memo=memo,
                user_id=user_id
            )
            db.session.add(transaction)
            transactions_added += 1
            
        except ValidationError as e:
            errors.append(f"Line {line_num}: {', '.join(e.args[0])}")
        except Exception as e:
            app.logger.error(f"Error processing line {line_num}: {str(e)}")
            errors.append(f"Line {line_num}: Unknown error occurred")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'error': 'Database error occurred',
            'transactions_added': 0,
            'errors': errors
        }), 500
    
    return jsonify({
        'message': 'Transactions processed',
        'transactions_added': transactions_added,
        'errors': errors
    }), 200 if transactions_added > 0 else 400

@app.route('/report', methods=['GET'])
@jwt_required()
def get_report():
    user_id = User.query.filter_by(username=get_jwt_identity()).first().id
    
    # Get optional date range filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query.filter_by(user_id=user_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date >= start)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.date <= end)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400
    
    transactions = query.all()
    
    gross_revenue = sum(t.amount for t in transactions if t.type == 'Income')
    expenses = sum(t.amount for t in transactions if t.type == 'Expense')
    net_revenue = gross_revenue - expenses
    
    return jsonify({
        'gross-revenue': float(gross_revenue),
        'expenses': float(expenses),
        'net-revenue': float(net_revenue),
        'transaction_count': len(transactions)
    })

@app.route('/transactions', methods=['GET'])
@jwt_required()
def list_transactions():
    user_id = User.query.filter_by(username=get_jwt_identity()).first().id
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    return jsonify([t.to_dict() for t in transactions])

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Finance Tracker API! Use /register, /login, /transactions, /report"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

