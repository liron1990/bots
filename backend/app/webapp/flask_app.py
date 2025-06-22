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
from users.app_config import AppConfig, BotConfig
from .auth import auth_bp, jwt_required, get_user_id_from_request
from app.utils.logger import setup_logger
import logging

app_config = AppConfig("services")
setup_logger(logger_name="Tor4UWebhook", log_dir=app_config.products_path / "logs", level=logging.DEBUG)

flask_app = Flask(__name__, static_folder='C:\\projects\\the_maze\\simple-hebrew-bot-studio\\dist')
CORS(flask_app)


def get_bot_config() -> BotConfig:
    user = get_user_id_from_request()
    if not user:
        return None
    return BotConfig(user)

# Register JWT-based auth routes
flask_app.register_blueprint(auth_bp, url_prefix="/api")

the_maze_app_config = AppConfig("the_maze", "tor4u")
config_yaml_manager = ConfigYamlManager(the_maze_app_config.config_path, the_maze_app_config.data_yaml_path)
webhook_handler = WebhookHandler(config_yaml_manager)

@flask_app.route('/webhook_fdw53etvn5ekndfetthg52cc352h97wps5', methods=['POST', 'GET'])
def tor4you_webhook():
    data = request.get_json(silent=True)
    return webhook_handler.handle(data)

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

@flask_app.route('/dashboard', methods=['GET'])
@jwt_required
def serve2(path):
    return send_from_directory(flask_app.static_folder, path)

@flask_app.route('/api/bot_messages', methods=['GET'])
@jwt_required
def get_yaml_as_json():
    bot_config = get_bot_config()
    if not bot_config:
        return jsonify({'error': 'Unauthorized'}), 401
    if not bot_config.data_yaml_path.exists():
        return jsonify({'error': 'File not found'}), 404
    manager = YamlManager(bot_config.data_yaml_path)
    data, err = manager.load()
    if err:
        return jsonify({'error': err}), 400
    return jsonify(data)

@flask_app.route('/api/bot_messages', methods=['POST'])
@jwt_required
def update_yaml_from_json():
    bot_config = get_bot_config()
    if not bot_config:
        return jsonify({'error': 'Unauthorized'}), 401
    manager = YamlManager(bot_config.data_yaml_path)
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

@atexit.register
def shutdown():
    config_yaml_manager.stop()
