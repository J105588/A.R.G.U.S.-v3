# main.py (パス問題を修正した最終版)

import os
import json
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO
from models import DatabaseManager

# ==============================================================================
# 初期設定
# ==============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key' 
socketio = SocketIO(app)

# このスクリプト自身の絶対パスを基準にすることで、実行場所に関わらずパスを固定する
project_root = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(project_root, 'argus.db')
config_dir = os.path.join(project_root, 'config')
domains_path = os.path.join(config_dir, "blocked_domains.txt")
state_path = os.path.join(config_dir, "state.json")

db_manager = DatabaseManager(db_path)

# --- 起動時のファイルチェック ---
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

if not os.path.exists(domains_path):
    with open(domains_path, 'w', encoding='utf-8') as f:
        f.write("# ここにブロックしたいドメインを1行ずつ記述します\n")

# 状態ファイルがなければデフォルト(有効)で作成
if not os.path.exists(state_path):
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump({'filtering_enabled': True}, f, indent=4)


# ==============================================================================
# バックエンドロジック (ファイル操作)
# ==============================================================================

# --- ドメイン管理ロジック ---
def read_domains_file():
    try:
        with open(domains_path, 'r', encoding='utf-8') as f:
            domains = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return domains
    except FileNotFoundError:
        return []

def write_domains_file(domains):
    try:
        unique_domains = sorted(list(set(d.strip().lower() for d in domains if d.strip())))
        with open(domains_path, 'w', encoding='utf-8') as f:
            f.write("# A.R.G.U.S. Blocked Domains List\n")
            f.write("# This file is managed by the web UI.\n")
            for domain in unique_domains:
                f.write(f"{domain}\n")
        return True
    except Exception as e:
        print(f"Error writing to domains file: {e}")
        return False

# --- フィルタリング状態管理ロジック ---
def read_filtering_state():
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return state.get('filtering_enabled', True)
    except (FileNotFoundError, json.JSONDecodeError):
        return True

def write_filtering_state(is_enabled: bool):
    try:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump({'filtering_enabled': is_enabled}, f, indent=4)
        return True
    except Exception as e:
        print(f"Error writing to state file: {e}")
        return False

# ==============================================================================
# APIエンドポイント
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/logs')
def get_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    logs, total_pages = db_manager.get_logs_paginated(page, per_page)
    return jsonify({
        'logs': [log.to_dict() for log in logs],
        'total_pages': total_pages,
        'current_page': page
    })

@app.route('/api/rules/domains', methods=['GET'])
def get_domains():
    return jsonify(read_domains_file())

@app.route('/api/rules/domains', methods=['POST'])
def add_domain():
    data = request.get_json()
    if not data or 'domain' not in data:
        return jsonify({'error': 'Domain not provided'}), 400
    new_domain = data['domain'].strip().lower()
    if not new_domain:
        return jsonify({'error': 'Domain cannot be empty'}), 400
    current_domains = read_domains_file()
    if new_domain in current_domains:
        return jsonify({'error': 'Domain already exists'}), 409
    current_domains.append(new_domain)
    if write_domains_file(current_domains):
        return jsonify({'success': True, 'domain': new_domain}), 201
    else:
        return jsonify({'error': 'Failed to write to config file'}), 500

@app.route('/api/rules/domains', methods=['DELETE'])
def delete_domain():
    data = request.get_json()
    if not data or 'domain' not in data:
        return jsonify({'error': 'Domain not provided'}), 400
    domain_to_delete = data['domain'].strip().lower()
    current_domains = read_domains_file()
    if domain_to_delete not in current_domains:
        return jsonify({'error': 'Domain not found'}), 404
    new_domains = [d for d in current_domains if d != domain_to_delete]
    if write_domains_file(new_domains):
        return jsonify({'success': True, 'domain': domain_to_delete}), 200
    else:
        return jsonify({'error': 'Failed to write to config file'}), 500

@app.route('/api/filtering/status', methods=['GET'])
def get_filtering_status():
    is_enabled = read_filtering_state()
    return jsonify({'is_enabled': is_enabled})

@app.route('/api/filtering/status', methods=['POST'])
def set_filtering_status():
    data = request.get_json()
    if data is None or 'is_enabled' not in data:
        return jsonify({'error': 'is_enabled parameter not provided'}), 400
    new_state = data.get('is_enabled')
    if not isinstance(new_state, bool):
         return jsonify({'error': 'is_enabled must be a boolean'}), 400
    if write_filtering_state(new_state):
        socketio.sleep(0.1) 
        socketio.emit('filtering_status_changed', {'is_enabled': new_state})
        return jsonify({'success': True, 'is_enabled': new_state})
    else:
        return jsonify({'error': 'Failed to write to state file'}), 500

# ==============================================================================
# SocketIOイベント
# ==============================================================================
@socketio.on('connect')
def handle_connect():
    print('Client connected to WebSocket')

# ==============================================================================
# アプリケーションの実行
# ==============================================================================
if __name__ == '__main__':
    # host='0.0.0.0' を指定して、同じネットワーク内の他のデバイスからアクセス可能にする
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)