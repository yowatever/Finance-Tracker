from datetime import datetime
from decimal import Decimal, InvalidOperation

class ValidationError(Exception):
    pass

def validate_transaction(date_str, trans_type, amount_str, memo):
    errors = []
    
    # Validate date
    try:
        date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD")
    
    # Validate type
    if trans_type.strip() not in ['Income', 'Expense']:
        errors.append("Type must be either 'Income' or 'Expense'")
    
    # Validate amount
    try:
        amount = Decimal(amount_str.replace('$', '').strip())
        if amount <= 0:
            errors.append("Amount must be positive")
    except InvalidOperation:
        errors.append("Invalid amount format")
    
    # Validate memo
    if not memo.strip():
        errors.append("Memo cannot be empty")
    if len(memo) > 200:
        errors.append("Memo must be less than 200 characters")
    
    if errors:
        raise ValidationError(errors)
    
    return date, trans_type.strip(), amount, memo.strip()
