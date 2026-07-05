from functools import wraps
from flask import abort
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def homeowner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'homeowner':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
