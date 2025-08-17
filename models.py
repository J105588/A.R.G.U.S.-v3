# models.py (修正後)

import sqlite3
from datetime import datetime

class TrafficLog:
    def __init__(self, id, timestamp, client_ip, method, url, status_code, is_blocked):
        self.id = id
        self.timestamp = timestamp
        self.client_ip = client_ip
        self.method = method
        self.url = url
        self.status_code = status_code
        self.is_blocked = is_blocked

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'client_ip': self.client_ip,
            'method': self.method,
            'url': self.url,
            'status_code': self.status_code,
            'is_blocked': self.is_blocked,
        }

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_logs_paginated(self, page=1, per_page=50):
        conn = self._get_db_connection()
        cursor = conn.cursor()

        # 総ログ数をカウント
        cursor.execute("SELECT COUNT(*) FROM traffic_logs")
        total_logs = cursor.fetchone()[0]
        total_pages = (total_logs + per_page - 1) // per_page

        # ページネーションでログを取得
        offset = (page - 1) * per_page
        cursor.execute("SELECT * FROM traffic_logs ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))
        
        logs_data = cursor.fetchall()
        conn.close()

        logs = [TrafficLog(**dict(row)) for row in logs_data]
        return logs, total_pages