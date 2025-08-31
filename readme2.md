# A.R.G.U.S. v3 システム完全解説書

## 目次
1. [システム概要](#システム概要)
2. [アーキテクチャ設計](#アーキテクチャ設計)
3. [コアコンポーネント詳細](#コアコンポーネント詳細)
4. [データフロー](#データフロー)
5. [設定ファイル仕様](#設定ファイル仕様)
6. [API仕様](#api仕様)
7. [フロントエンド詳細](#フロントエンド詳細)
8. [データベース設計](#データベース設計)
9. [セキュリティ機能](#セキュリティ機能)
10. [運用・保守](#運用保守)
11. [トラブルシューティング](#トラブルシューティング)
12. [開発者向け情報](#開発者向け情報)

---

## システム概要

### 基本情報
- **名称**: A.R.G.U.S. v3 (Active Routing & Guarding Utility Service)
- **目的**: ローカル環境での高機能フィルタリング・プロキシシステム
- **動作環境**: Windows 10/11, Python 3.8+
- **ライセンス**: MIT License

### 主要機能
1. **リアルタイムフィルタリング**: ドメインベースのアクセス制御
2. **Web管理ダッシュボード**: 直感的なUIでの設定・監視
3. **通信ログ記録**: すべてのHTTP/HTTPS通信の詳細記録
4. **カスタムブロックページ**: ユーザー定義のブロック画面
5. **ホワイトリスト/ブラックリストモード**: 柔軟な制御方式
6. **リアルタイム監視**: mitmwebによる通信フロー可視化

---

## アーキテクチャ設計

### システム構成図
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser  │    │  Other Clients  │    │  Mobile Apps   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    A.R.G.U.S. Proxy      │
                    │        (Port 8080)       │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   proxy_addon.py         │
                    │   (mitmproxy addon)      │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│  Web Dashboard   │  │  Traffic Logs     │  │  Block Rules     │
│   (Port 5000)    │  │   (SQLite DB)     │  │  (Text Files)    │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

### コンポーネント間の関係
- **proxy_addon.py**: プロキシの中核処理、フィルタリングロジック
- **main.py**: Webダッシュボードサーバー、API提供
- **templates/**: ユーザーインターフェース
- **static/**: フロントエンドのJavaScript/CSS
- **config/**: 設定ファイル群
- **argus.db**: SQLiteデータベース

---

## コアコンポーネント詳細

### 1. proxy_addon.py (プロキシアドオン)

#### クラス構造
```python
class ArgusProxyAddon:
    def __init__(self):
        # 初期化処理
        # パス設定、データベース接続、ルール読み込み
    
    def load_rules_and_state(self):
        # 設定ファイルの動的読み込み
    
    def request(self, flow: http.HTTPFlow):
        # リクエスト処理・フィルタリング
    
    def response(self, flow: http.HTTPFlow):
        # レスポンス処理・ログ記録
```

#### 主要機能
1. **フィルタリングエンジン**
   - ブラックリストモード: 指定ドメインをブロック
   - ホワイトリストモード: 許可リスト以外をブロック
   - サブドメイン対応: `example.com`で`sub.example.com`も制御

2. **動的設定更新**
   - ファイル変更監視による即座反映
   - 再起動不要の設定変更

3. **カスタムブロックページ**
   - HTMLテンプレートの動的生成
   - ブロック理由の詳細表示

#### フィルタリングロジック
```python
if self.whitelist_mode:
    # ホワイトリストモード
    matched = False
    for allowed_domain in self.allowed_domains:
        if request_host == allowed_domain or request_host.endswith("." + allowed_domain):
            matched = True
            break
    if not matched:
        is_blocked = True
else:
    # ブラックリストモード
    for blocked_domain in self.blocked_domains:
        if request_host == blocked_domain or request_host.endswith("." + blocked_domain):
            is_blocked = True
            break
```

### 2. main.py (Webサーバー)

#### Flaskアプリケーション構造
```python
app = Flask(__name__)

# ルーティング定義
@app.route('/')                    # メインダッシュボード
@app.route('/api/rules/domains')   # ドメイン管理API
@app.route('/api/logs')            # ログ取得API
@app.route('/api/filtering/status') # フィルタリング状態API
```

#### API設計原則
- **RESTful設計**: GET/POST/DELETEメソッドの適切な使用
- **JSON形式**: データ交換の標準化
- **エラーハンドリング**: 適切なHTTPステータスコード
- **セキュリティ**: 入力値の検証・サニタイゼーション

#### 主要APIエンドポイント

##### ドメイン管理API
```python
@app.route('/api/rules/domains', methods=['GET', 'POST', 'DELETE'])
def manage_domains():
    if request.method == 'GET':
        # ブロックドメイン一覧取得
    elif request.method == 'POST':
        # 新規ドメイン追加
    elif request.method == 'DELETE':
        # ドメイン削除
```

##### ログ取得API
```python
@app.route('/api/logs', methods=['GET'])
def get_logs():
    # SQLiteから最新100件のログを取得
    # ページネーション対応
```

### 3. models.py (データモデル)

#### TrafficLogクラス
```python
class TrafficLog:
    def __init__(self, id, timestamp, client_ip, method, url, status_code, is_blocked):
        # 通信ログのデータ構造
    
    def to_dict(self):
        # 辞書形式でのデータ出力
```

#### DatabaseManagerクラス
```python
class DatabaseManager:
    def get_logs_paginated(self, page=1, per_page=50):
        # ページネーション対応のログ取得
        # 総ページ数計算
```

---

## データフロー

### 1. リクエスト処理フロー
```
1. クライアント → プロキシ (Port 8080)
2. proxy_addon.py でリクエスト解析
3. フィルタリングルール適用
4. ブロック判定
   ├─ ブロック対象 → カスタムページ表示
   └─ 許可対象 → 通常のプロキシ処理
5. レスポンス生成・返送
6. ログ記録 (SQLite DB)
```

### 2. 設定更新フロー
```
1. Web UI で設定変更
2. API呼び出し (POST/DELETE)
3. 設定ファイル更新
4. proxy_addon.py でファイル変更検知
5. メモリ内ルール更新
6. 即座にフィルタリングに反映
```

### 3. ログ記録フロー
```
1. HTTPリクエスト/レスポンス処理
2. 通信情報抽出
   - タイムスタンプ
   - クライアントIP
   - HTTPメソッド
   - URL
   - ステータスコード
   - ブロック判定結果
3. SQLite DB にINSERT
4. Web UI でリアルタイム表示
```

---

## 設定ファイル仕様

### 1. config/state.json
```json
{
    "filtering_enabled": true,    // フィルタリング有効/無効
    "whitelist_mode": false      // ホワイトリストモード有効/無効
}
```

### 2. config/blocked_domains.txt
```
# ブロック対象ドメイン (ブラックリスト)
# コメント行は # で開始
example.com
malware-site.org
ads.example.net
```

### 3. config/allowed_domains.txt
```
# 許可対象ドメイン (ホワイトリスト)
# ホワイトリストモード時のみ使用
trusted-site.com
secure.example.org
```

### 4. config/blocked_keywords.txt
```
# キーワードベースのブロック (将来実装予定)
# 現在は未使用
```

---

## API仕様

### 1. ドメイン管理API

#### GET /api/rules/domains
- **目的**: ブロックドメイン一覧取得
- **レスポンス**: `["domain1.com", "domain2.org"]`
- **エラー**: ファイル不存在時は空配列

#### POST /api/rules/domains
- **目的**: 新規ブロックドメイン追加
- **リクエスト**: `{"domain": "example.com"}`
- **レスポンス**: `{"message": "Domain added"}`

#### DELETE /api/rules/domains
- **目的**: ブロックドメイン削除
- **リクエスト**: `{"domain": "example.com"}`
- **レスポンス**: `{"message": "Domain deleted"}`

### 2. 許可ドメイン管理API

#### GET /api/rules/allowed_domains
- **目的**: 許可ドメイン一覧取得
- **レスポンス**: `["trusted.com", "secure.org"]`

#### POST /api/rules/allowed_domains
- **目的**: 新規許可ドメイン追加
- **リクエスト**: `{"domain": "trusted.com"}`

#### DELETE /api/rules/allowed_domains
- **目的**: 許可ドメイン削除
- **リクエスト**: `{"domain": "trusted.com"}`

### 3. フィルタリング状態API

#### GET /api/filtering/status
- **目的**: フィルタリング有効/無効状態取得
- **レスポンス**: `{"is_enabled": true}`

#### POST /api/filtering/status
- **目的**: フィルタリング状態変更
- **リクエスト**: `{"is_enabled": false}`

### 4. ホワイトリストモードAPI

#### GET /api/filtering/whitelist_mode
- **目的**: ホワイトリストモード状態取得
- **レスポンス**: `{"is_enabled": false}`

#### POST /api/filtering/whitelist_mode
- **目的**: ホワイトリストモード状態変更
- **リクエスト**: `{"is_enabled": true}`

### 5. ログ取得API

#### GET /api/logs
- **目的**: 通信ログ取得
- **レスポンス**: 
```json
{
    "logs": [
        {
            "timestamp": "2024-01-01T12:00:00",
            "client_ip": "192.168.1.100",
            "method": "GET",
            "url": "https://example.com/page",
            "status_code": 200,
            "is_blocked": false
        }
    ]
}
```

---

## フロントエンド詳細

### 1. HTML構造 (templates/index.html)

#### タブベースUI設計
```html
<div class="nav-tabs">
    <button class="tab-button active" onclick="showTab('dashboard')">ダッシュボード</button>
    <button class="tab-button" onclick="showTab('rules')">ルール管理</button>
    <button class="tab-button" onclick="showTab('logs')">通信ログ</button>
    <button class="tab-button" onclick="showTab('settings')">設定</button>
</div>
```

#### レスポンシブデザイン
- CSS Grid/Flexboxによるレイアウト
- モバイル対応のビューポート設定
- ダークテーマによる視認性向上

### 2. JavaScript機能 (static/js/app.js)

#### タブ管理システム
```javascript
function showTab(tabName) {
    // 全タブコンテンツを非表示
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    // 全タブボタンのアクティブ状態を解除
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    // 指定タブを表示・アクティブ化
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`.tab-button[onclick="showTab('${tabName}')"]`).classList.add('active');
}
```

#### 非同期通信処理
```javascript
async function loadBlockedDomains() {
    try {
        const response = await fetch('/api/rules/domains');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const domains = await response.json();
        // DOM更新処理
    } catch (error) {
        console.error('Failed to load domains:', error);
        // エラー表示処理
    }
}
```

#### リアルタイム更新
- 定期的なAPI呼び出しによる状態更新
- ユーザー操作による即座反映
- エラーハンドリングとユーザーフィードバック

### 3. CSS設計 (static/css/)

#### デザインシステム
- **カラーパレット**: ダークテーマベース
- **タイポグラフィ**: Segoe UI + Meiryo
- **コンポーネント**: カード、ボタン、フォームの統一デザイン
- **アニメーション**: ホバー効果、トランジション

---

## データベース設計

### 1. SQLiteスキーマ

#### traffic_logs テーブル
```sql
CREATE TABLE traffic_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,           -- ISO形式タイムスタンプ
    client_ip TEXT,           -- クライアントIPアドレス
    method TEXT,              -- HTTPメソッド (GET, POST等)
    url TEXT,                 -- リクエストURL
    status_code INTEGER,      -- HTTPステータスコード
    is_blocked BOOLEAN        -- ブロック判定結果
);
```

### 2. データ型と制約
- **id**: 自動インクリメント主キー
- **timestamp**: ISO 8601形式文字列
- **client_ip**: IPv4/IPv6アドレス文字列
- **method**: HTTPメソッド文字列
- **url**: 完全URL文字列
- **status_code**: HTTPステータスコード整数
- **is_blocked**: 真偽値 (0/1)

### 3. インデックス戦略
```sql
-- タイムスタンプによる検索最適化
CREATE INDEX idx_timestamp ON traffic_logs(timestamp);

-- クライアントIPによる検索最適化
CREATE INDEX idx_client_ip ON traffic_logs(client_ip);

-- ブロック判定による検索最適化
CREATE INDEX idx_is_blocked ON traffic_logs(is_blocked);
```

### 4. データ管理
- **自動クリーンアップ**: 古いログの自動削除
- **バックアップ**: 定期的なDBファイルバックアップ
- **整合性チェック**: 定期的なDB整合性検証

---

## セキュリティ機能

### 1. プロキシレベルセキュリティ
- **HTTPS傍受**: mitmproxyによる証明書管理
- **証明書検証**: クライアント側での証明書信頼設定
- **通信暗号化**: TLS/SSL通信の適切な処理

### 2. Webアプリケーションセキュリティ
- **入力値検証**: ドメイン名の形式チェック
- **SQLインジェクション対策**: パラメータ化クエリ使用
- **XSS対策**: 出力エスケープ処理
- **CSRF対策**: 適切なHTTPメソッド使用

### 3. ネットワークセキュリティ
- **ポート制限**: 必要最小限のポート開放
- **IP制限**: ローカルホストからのアクセスのみ
- **プロキシ認証**: 必要に応じた認証機能

### 4. ログセキュリティ
- **機密情報保護**: パスワード等の機密データ除外
- **ログローテーション**: 古いログの自動削除
- **アクセス制御**: ログファイルへの不正アクセス防止

---

## 運用・保守

### 1. 起動プロセス

#### final-start.bat の動作
```batch
1. 仮想環境の存在確認
2. Python仮想環境の有効化
3. Flask Webサーバー起動 (Port 5000)
4. mitmweb起動 (Port 8081, Proxy Port 8080)
```

#### 起動順序
1. **仮想環境チェック**: venvフォルダの存在確認
2. **Webサーバー起動**: Flaskアプリケーション開始
3. **プロキシ起動**: mitmproxy + カスタムアドオン
4. **サービス確認**: 各ポートでの動作確認

### 2. 監視・ログ管理

#### システムログ
- **mitmproxyログ**: プロキシレベルの詳細ログ
- **Flaskログ**: Webアプリケーションの動作ログ
- **エラーログ**: 例外・エラーの詳細記録

#### パフォーマンス監視
- **メモリ使用量**: プロキシアドオンのメモリ消費
- **CPU使用率**: フィルタリング処理の負荷
- **ディスクI/O**: ログ記録・設定ファイル読み込み

### 3. バックアップ・復旧

#### 設定ファイルバックアップ
```bash
# 設定ファイルの定期バックアップ
config/
├── blocked_domains.txt.backup
├── allowed_domains.txt.backup
├── state.json.backup
└── settings.json.backup
```

#### データベースバックアップ
```bash
# SQLite DBの定期バックアップ
argus.db.backup
argus.db.backup.$(date +%Y%m%d)
```

### 4. 更新・メンテナンス

#### ライブラリ更新
```bash
# 依存関係の更新
pip install --upgrade mitmproxy flask sqlalchemy

# セキュリティパッチの適用
pip install --upgrade --only-binary=all
```

#### 設定ファイル更新
- ドメインリストの定期的な見直し
- ブロックルールの最適化
- パフォーマンス設定の調整

---

## トラブルシューティング

### 1. よくある問題と解決方法

#### プロキシ接続エラー
**症状**: クライアントがプロキシに接続できない
**原因**: 
- ポート8080が使用中
- ファイアウォール設定
- プロキシサービスが起動していない

**解決方法**:
```bash
# ポート使用状況確認
netstat -an | findstr :8080

# プロキシサービス再起動
# final-start.bat を再実行
```

#### HTTPS証明書エラー
**症状**: ブラウザで証明書警告が表示される
**原因**: mitmproxy証明書がクライアントに信頼されていない

**解決方法**:
1. `http://mitm.it` にアクセス
2. OS別の証明書をダウンロード
3. 証明書を「信頼されたルート証明機関」にインストール

#### Webダッシュボードアクセスエラー
**症状**: `http://127.0.0.1:5000` にアクセスできない
**原因**: Flaskサーバーが起動していない

**解決方法**:
```bash
# Flaskプロセスの確認
tasklist | findstr python

# ログファイルの確認
# エラーメッセージの詳細確認
```

### 2. ログ分析による問題特定

#### プロキシログの確認
```bash
# mitmproxyのログ出力確認
# コンソールでのエラーメッセージ確認
```

#### Webサーバーログの確認
```bash
# Flaskアプリケーションのログ確認
# ブラウザの開発者ツールでのエラー確認
```

#### データベースログの確認
```bash
# SQLite DBの整合性チェック
sqlite3 argus.db "PRAGMA integrity_check;"
```

### 3. パフォーマンス問題

#### メモリ使用量の最適化
- ログレコード数の制限
- 古いログの自動削除
- メモリリークの監視

#### フィルタリング速度の最適化
- ドメインリストの最適化
- 正規表現の効率化
- キャッシュ機能の活用

---

## 開発者向け情報

### 1. 開発環境セットアップ

#### 必要なツール
```bash
# Python 3.8+
python --version

# Git
git --version

# 仮想環境
python -m venv venv
```

#### 依存関係のインストール
```bash
# 開発用依存関係
pip install -r requirements.txt

# 開発ツール
pip install pytest black flake8
```

### 2. コード品質管理

#### コーディング規約
- **Python**: PEP 8準拠
- **JavaScript**: ESLint設定準拠
- **HTML/CSS**: セマンティックなマークアップ

#### テスト戦略
```python
# 単体テスト
pytest tests/

# 統合テスト
pytest tests/integration/

# パフォーマンステスト
pytest tests/performance/
```

### 3. 拡張開発

#### 新しいフィルタリングルールの追加
```python
# proxy_addon.py に新しいルールタイプを追加
def custom_filtering_rule(self, request_host):
    # カスタムフィルタリングロジック
    pass
```

#### 新しいAPIエンドポイントの追加
```python
# main.py に新しいルートを追加
@app.route('/api/custom/endpoint', methods=['GET'])
def custom_endpoint():
    # カスタムAPI処理
    pass
```

#### フロントエンド機能の拡張
```javascript
// app.js に新しい機能を追加
function customFunction() {
    // カスタム機能の実装
}
```

### 4. デバッグ・開発支援

#### ログレベルの調整
```python
# 開発時の詳細ログ出力
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 開発用設定
```json
// config/development.json
{
    "debug_mode": true,
    "log_level": "DEBUG",
    "auto_reload": true
}
```

#### ホットリロード
```bash
# 開発時の自動再起動
flask run --debug --reload
```

---

## まとめ

A.R.G.U.S. v3は、ローカル環境での高機能フィルタリング・プロキシシステムとして設計されており、以下の特徴を持っています：

### 技術的特徴
- **モジュラー設計**: 各コンポーネントの独立性と拡張性
- **リアルタイム処理**: 設定変更の即座反映
- **スケーラビリティ**: 小規模から中規模環境への対応
- **保守性**: 明確なコード構造とドキュメント

### 運用上の利点
- **簡単なセットアップ**: バッチファイルによるワンクリック起動
- **柔軟な設定**: ブラックリスト/ホワイトリストモードの切り替え
- **包括的な監視**: Web UI + リアルタイムコンソール
- **安定した動作**: Python仮想環境による依存関係の分離

### 今後の発展可能性
- **AI/ML統合**: 機械学習による自動フィルタリング
- **クラウド連携**: 設定の同期・バックアップ
- **モバイル対応**: スマートフォン・タブレット向けアプリ
- **API拡張**: 外部システムとの連携機能

このシステムは、個人ユーザーから小規模組織まで、様々なニーズに対応できる柔軟性と拡張性を備えた、実用的なネットワークセキュリティソリューションです。
