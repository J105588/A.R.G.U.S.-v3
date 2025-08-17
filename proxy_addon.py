# proxy_addon.py (blocked_page.html を使用する最終版)

import os
import sqlite3
from datetime import datetime
import json
from mitmproxy import http, ctx

class ArgusProxyAddon:
    def __init__(self):
        # --- パス設定 ---
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.project_root, 'argus.db')
        self.config_dir = os.path.join(self.project_root, 'config')
        self.domains_path = os.path.join(self.config_dir, "blocked_domains.txt")
        self.state_path = os.path.join(self.config_dir, "state.json")
        # ★★★ ブロックページのテンプレートへのパスを追加 ★★★
        self.block_page_path = os.path.join(self.project_root, 'templates', 'blocked_page.html')

        # --- 変数初期化 ---
        self.db_conn = None
        self.blocked_domains = set()
        self.filtering_enabled = True
        self.last_mtime = 0
        self.last_state_mtime = 0
        # ★★★ ブロックページのHTMLをキャッシュする変数を追加 ★★★
        self.block_page_template = ""

        # --- 初期化処理 ---
        ctx.log.info(f"Initializing A.R.G.U.S. Proxy Addon. Project root: {self.project_root}")
        self.setup_database()
        self.load_block_page() # 初回起動時にテンプレートを読み込む
        self.load_rules_and_state()
        ctx.log.info("A.R.G.U.S. Proxy Addon is now active.")

    def load_rules_and_state(self):
        """設定ファイルと状態ファイルを読み込む"""
        try:
            current_state_mtime = os.path.getmtime(self.state_path)
            if current_state_mtime > self.last_state_mtime:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.filtering_enabled = state.get('filtering_enabled', True)
                self.last_state_mtime = current_state_mtime
                ctx.log.info(f"Filtering state reloaded. Enabled: {self.filtering_enabled}")
        except (FileNotFoundError, json.JSONDecodeError):
            self.filtering_enabled = True
        
        try:
            current_mtime = os.path.getmtime(self.domains_path)
            if current_mtime > self.last_mtime:
                with open(self.domains_path, 'r', encoding='utf-8') as f:
                    self.blocked_domains = {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}
                self.last_mtime = current_mtime
                ctx.log.info(f"Rules reloaded. {len(self.blocked_domains)} domains loaded.")
        except FileNotFoundError:
            self.blocked_domains = set()

    # ★★★ ブロックページのHTMLを読み込む関数を新規追加 ★★★
    def load_block_page(self):
        """blocked_page.htmlを読み込み、メモリにキャッシュする"""
        try:
            with open(self.block_page_path, 'r', encoding='utf-8') as f:
                self.block_page_template = f.read()
            ctx.log.info(f"Successfully loaded block page template from: {self.block_page_path}")
        except FileNotFoundError:
            ctx.log.error(f"FATAL: Block page template not found at '{self.block_page_path}'!")
            ctx.log.error("Using a basic fallback block page.")
            self.block_page_template = """
            <html><head><title>Access Denied</title></head>
            <body><h1>403 Forbidden</h1><p>Access to {{BLOCKED_URL}} was denied by A.R.G.U.S.</p>
            <p>Error: Custom block page template is missing.</p></body></html>
            """

    def setup_database(self):
        """データベース接続をセットアップする"""
        try:
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                client_ip TEXT,
                method TEXT,
                url TEXT,
                status_code INTEGER,
                is_blocked BOOLEAN
            )
            ''')
            self.db_conn.commit()
        except sqlite3.Error as e:
            ctx.log.error(f"Database Error: {e}")
            self.db_conn = None

    def log_request_to_db(self, flow, is_blocked):
        """リクエスト情報をデータベースに保存する"""
        if not self.db_conn: return
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "INSERT INTO traffic_logs (timestamp, client_ip, method, url, status_code, is_blocked) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    flow.client_conn.peername[0],
                    flow.request.method,
                    flow.request.pretty_url,
                    flow.response.status_code if flow.response else 0,
                    is_blocked,
                )
            )
            self.db_conn.commit()
        except sqlite3.Error as e:
            ctx.log.error(f"Failed to log request to DB: {e}")

    def request(self, flow: http.HTTPFlow):
        """すべてのリクエストを処理する"""
        # ルールと状態を定期的にチェックして再読み込み
        self.load_rules_and_state()

        if not self.filtering_enabled:
            return

        request_host = flow.request.host.lower()
        
        # ブロック対象かチェック
        matched_domain = None
        for blocked_domain in self.blocked_domains:
            if request_host == blocked_domain or request_host.endswith("." + blocked_domain):
                matched_domain = blocked_domain
                break
        
        if matched_domain:
            ctx.log.info(f"BLOCKED: {flow.request.pretty_url} (Reason: Matched domain '{matched_domain}')")
            
            # ★★★ ここからがブロックページの生成処理 ★★★
            # 1. プレースホルダーを実際の値で置き換える
            reason_text = f"The domain '{request_host}' is on the block list (matched rule: '{matched_domain}')."
            blocked_url_text = flow.request.pretty_url
            
            # 2. テンプレートの文字列を置換
            content = self.block_page_template.replace("{{ REASON }}", reason_text)
            content = content.replace("{{ BLOCKED_URL }}", blocked_url_text)
            
            # 3. 置換後のHTMLでレスポンスを作成
            flow.response = http.Response.make(
                403,
                content.encode('utf-8'),
                {"Content-Type": "text/html; charset=utf-8"}
            )

    def response(self, flow: http.HTTPFlow):
        """レスポンスをDBにログ記録する"""
        is_blocked = bool(flow.response and flow.response.status_code == 403 and flow.response.headers.get("Content-Type", "").startswith("text/html"))
        if is_blocked:
             # ブロック済みの場合、requestフェーズでレスポンスが作られているので、その内容を使ってログを記録
             pass
        self.log_request_to_db(flow, is_blocked)

addons = [ArgusProxyAddon()]