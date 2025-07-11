from flask import Blueprint, jsonify, request
import json
from app.utils.yaml_manager import YamlManager
from app.webapp.auth import get_user_id_from_request, user_or_admin_required
from users.user_paths import BotPaths, Tor4Paths


users_api = Blueprint("users_api", __name__)


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

@users_api.route('/api/<user_id>/bot_messages', methods=['GET', 'POST'])
@user_or_admin_required
def bot_messages(user_id):
    bot_config = get_bot_paths(user_id)
    return handle_yaml_messages(bot_config, request.method)

@users_api.route('/api/<user_id>/tor4u_messages', methods=['GET', 'POST'])
@user_or_admin_required
def tor4u_messages(user_id):
    tor4u_config = get_tor4u_paths(user_id)
    return handle_yaml_messages(tor4u_config, request.method)

@users_api.route('/api/<user_id>/prompt', methods=['GET', 'POST'])
@user_or_admin_required
def prompt_file(user_id):
    bot_config = get_bot_paths(user_id)
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

@users_api.route('/api/<user_id>/settings', methods=['GET', 'POST'])
@user_or_admin_required
def user_settings(user_id):
    bot_config = get_bot_paths(user_id)
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


def get_bot_paths(user_id: str) -> BotPaths:
    return BotPaths(user_id)

def get_tor4u_paths(user_id: str) -> Tor4Paths:
    return Tor4Paths(user_id)
