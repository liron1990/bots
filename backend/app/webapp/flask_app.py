# app/main.py (or wherever your Flask app is initialized)

from flask import Flask, send_from_directory, jsonify, request
from pathlib import Path
from flask_cors import CORS
import json
from app.utils.yaml_manager import YamlManager
from app.common.tor4u.webhook_handler import WebhookHandler
from users.user_paths import Paths, BotPaths, Tor4Paths
from .auth import auth_bp, jwt_required, get_user_id_from_request
from app.utils.logger import setup_logger
import logging
from .admin.admin_api import admin_api
from .users_config.config_api import users_api
from users.users import Users

app_paths = Paths("services", "webapp", make_dirs=True)
setup_logger(logger_name="Tor4UWebhook", log_dir=app_paths.products_path / "logs", level=logging.DEBUG)

flask_app = Flask(__name__, static_folder=str(app_paths.programs_dir / "static"), static_url_path='/static')
CORS(flask_app)



# Register JWT-based auth routes
flask_app.register_blueprint(auth_bp, url_prefix="/api")
flask_app.register_blueprint(admin_api)  # Register admin API
flask_app.register_blueprint(users_api)  # Register users API


handlers = {"the_maze": WebhookHandler("the_maze")}
users = Users()

@flask_app.route('/webhook_fdw53etvn5ekndfetthg52cc352h97wps5', methods=['POST', 'GET'])
def tor4you_webhook():
    data = request.get_json(silent=True)
    return handlers["the_maze"].handle(data)

@flask_app.route('/b737d939-6d7e-4a2b-adb9-2085e6ae883b/<guid>', methods=['POST', 'GET'])
def tor4you_generic_webhook(guid: str):
    print("Received GUID:", guid)  # or use it in logic
    user_name = users.get_user(guid)
    
    if user_name not in handlers:
        handlers[user_name] = WebhookHandler(user_name)
    
    data = request.get_json(silent=True)
    return handlers[user_name].handle(data)

@flask_app.route('/486ea3ce-17f6-4a1a-b1f8-d5c83751453e/<guid>', methods=['POST', 'GET'])
def send_message(guid: str):
    print("Received GUID:", guid)  # or use it in logic
    user_name = users.get_user(guid)
    
    if user_name not in handlers:
        handlers[user_name] = WebhookHandler(user_name)
    
    data = request.args.to_dict()
    return handlers[user_name].handle_send_message(data)

@flask_app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

@flask_app.route('/api/protected')
@jwt_required
def protected():
    user = get_user_id_from_request()
    return jsonify({'data': f'Secret data for {user} only'})

@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def serve(path):
    file_path = Path(flask_app.static_folder) / path
    if path != "" and file_path.exists():
        return send_from_directory(flask_app.static_folder, path)
    else:
        return send_from_directory(flask_app.static_folder, 'index.html')


