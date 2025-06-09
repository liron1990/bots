from flask import Blueprint, request, jsonify
from functools import wraps
import jwt, datetime

SECRET = "gsdfW#@$@#sdsc34"  # use env var in prod

auth_bp = Blueprint("auth", __name__)

# Dummy user store (replace with DB in real app)
USERS = {"The_maze": "Aa1234"}

def get_token_from_header():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = decode_token(token)
            request.user = payload["user_id"]
        except Exception as e:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user_id=username)
    return jsonify({"token": token})

@auth_bp.route("/protected", methods=["GET"])
@jwt_required
def protected():
    return jsonify({"msg": f"Hello {request.user}!"})



def get_user_id_from_request():
    token = get_token_from_header()
    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload["user_id"]
    except:
        return None

def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])