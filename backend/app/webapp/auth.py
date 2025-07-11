from flask import Blueprint, request, jsonify
from functools import wraps
import jwt, datetime
import json
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect
from users.user_paths import Paths
from users.users import Users

SECRET = "gsdfW#@$@#sdsc34"  # use env var in prod

auth_bp = Blueprint("auth", __name__)

app_paths = Paths("services", make_dirs=True)
USERS_FILE = app_paths.user_data_path / "users_auth.json"

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

USERS = load_users()

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
            return redirect("/login")
        try:
            payload = decode_token(token)
            request.user = payload["user_id"]
        except Exception as e:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    users = load_users()
    stored_hash = users.get(username)
    if not stored_hash or not check_password_hash(stored_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user_id=username)
    return jsonify({"token": token})

@auth_bp.route("/protected", methods=["GET"])
@jwt_required
def protected():
    return jsonify({"msg": f"Hello {request.user}!"})

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": "Username already exists"}), 400

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    users[username] = hashed_pw
    save_users(users)
    return jsonify({"success": True})

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
    users = Users()
    role = "admin" if users.is_admin(user_id) else "user"
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=3),
        "iat": datetime.datetime.utcnow(),
        "role": role
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])

@auth_bp.route("/auth/check-role", methods=["GET"])
@jwt_required
def check_role():
    user_id = get_user_id_from_request()
    if user_id == "admin":
        return jsonify({"role": "admin"})
    else:
        return jsonify({"role": "user"})