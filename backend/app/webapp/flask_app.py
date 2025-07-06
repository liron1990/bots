# app/main.py (or wherever your Flask app is initialized)

from flask import Flask, send_from_directory, jsonify, request
from pathlib import Path
from flask_cors import CORS
import os
import json
import atexit
from app.common.config_yaml_manager import ConfigYamlManager
from app.utils.yaml_manager import YamlManager
from app.common.tor4u.webhook_handler import WebhookHandler
from users.app_config import AppConfig, BotConfig, Tor4uConfig
from .auth import auth_bp, jwt_required, get_user_id_from_request
from app.utils.logger import setup_logger
import logging
from .admin_api import admin_api
from users.users import Users

app_config = AppConfig("services", "webapp")
setup_logger(logger_name="Tor4UWebhook", log_dir=app_config.products_path / "logs", level=logging.DEBUG)

flask_app = Flask(__name__, static_folder=str(app_config.programs_dir / "static"), static_url_path='/static')
CORS(flask_app)


def get_bot_config() -> BotConfig:
    user = get_user_id_from_request()
    if not user:
        return None
    return BotConfig(user)

def get_tor4u_config() -> Tor4uConfig:
    user = get_user_id_from_request()
    if not user:
        return None
    return Tor4uConfig(user)

# Register JWT-based auth routes
flask_app.register_blueprint(auth_bp, url_prefix="/api")
flask_app.register_blueprint(admin_api)  # Register admin API


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


def handle_yaml_messages(config, method):
    if not config:
        return jsonify({'error': 'Unauthorized'}), 401
    manager = YamlManager(config.data_yaml_path)
    if method == 'GET':
        if not config.data_yaml_path.exists():
            return jsonify({'error': 'File not found'}), 404
        data, err = manager.load()
        if err:
            return jsonify({'error': err}), 400
        return jsonify(data)
    elif method == 'POST':
        original_yaml, err = manager.load()
        if err:
            return jsonify({'error': err}), 400
        new_data = request.json

        key_check_passed, changes = manager.check_key_structure(original_yaml, new_data)
        if not key_check_passed:
            for change in changes:
                print(change)
            return jsonify({'error': 'Keys/structure cannot be changed.'}), 400

        manager.update_values_only(original_yaml, new_data)
        success, err = manager.dump(original_yaml)
        if not success:
            return jsonify({'error': err}), 400
        return jsonify({'success': True})

@flask_app.route('/api/bot_messages', methods=['GET', 'POST'])
@jwt_required
def bot_messages():
    bot_config = get_bot_config()
    return handle_yaml_messages(bot_config, request.method)

@flask_app.route('/api/tor4u_messages', methods=['GET', 'POST'])
@jwt_required
def tor4u_messages():
    tor4u_config = get_tor4u_config()
    return handle_yaml_messages(tor4u_config, request.method)

@flask_app.route('/api/prompt', methods=['GET', 'POST'])
@jwt_required
def prompt_file():
    bot_config = get_bot_config()
    if not bot_config:
        return jsonify({'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        if not bot_config.prompt_path.exists():
            return jsonify({'prompt': ''})
        return jsonify({'prompt': bot_config.prompt_path.read_text(encoding='utf-8')})
    else:
        data = request.json
        prompt = data.get('prompt', '')
        bot_config.prompt_path.write_text(prompt, encoding='utf-8')
        return jsonify({'success': True})

@flask_app.route('/api/settings', methods=['GET', 'POST'])
@jwt_required
def user_settings():
    bot_config = get_bot_config()
    if not bot_config:
        return jsonify({'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        if not bot_config.config_path.exists():
            return jsonify({})
        return jsonify(json.loads(bot_config.config_path.read_text(encoding='utf-8')))
    else:
        data = request.json
        bot_config.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return jsonify({'success': True})

