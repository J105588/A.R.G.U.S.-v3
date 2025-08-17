// app.js (更新ボタン復活バージョン)

document.addEventListener('DOMContentLoaded', function() {
    // 初期タブを表示
    showTab('dashboard');
    
    // 初期データの読み込み（ダッシュボードタブを開いた時に通信ログを一度読み込む）
    initializeDashboard();

    // タブ切り替え時のイベントリスナー
    document.querySelector('.nav-tabs').addEventListener('click', function(event) {
        if (event.target.classList.contains('tab-button')) {
            const tabName = event.target.getAttribute('onclick').replace("showTab('", "").replace("')", "");
            // 「ルール管理」タブを開いた時だけ、その内容を読み込む
            if (tabName === 'rules') {
                loadBlockedDomains();
                loadFilteringStatus();
            }
        }
    });

    // ドメイン入力欄でEnterキーを押したら追加ボタンをクリックする
    document.getElementById('new-domain').addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            document.querySelector('.add-rule button[onclick="addDomain()"]').click();
        }
    });

    // モーダルの外側をクリックしたら閉じる
    window.onclick = function(event) {
        const modal = document.getElementById('detail-modal');
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});

// =============================================================================
// タブ切り替え機能
// =============================================================================
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`.tab-button[onclick="showTab('${tabName}')"]`).classList.add('active');
}

// =============================================================================
// ルール管理機能
// =============================================================================

// --- ドメイン管理 ---
async function loadBlockedDomains() {
    console.log("Loading blocked domains...");
    try {
        const response = await fetch('/api/rules/domains');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const domains = await response.json();
        const listElement = document.getElementById('domains-list');
        listElement.innerHTML = '';
        if (domains.length === 0) {
            listElement.innerHTML = '<li class="rule-item empty">ブロック中のドメインはありません。</li>';
        } else {
            domains.forEach(domain => {
                const li = document.createElement('li');
                li.className = 'rule-item';
                li.textContent = domain;
                const deleteButton = document.createElement('button');
                deleteButton.textContent = '削除';
                deleteButton.className = 'btn btn-danger';
                deleteButton.onclick = () => deleteDomain(domain);
                li.appendChild(deleteButton);
                listElement.appendChild(li);
            });
        }
    } catch (error) {
        console.error('Failed to load domains:', error);
        document.getElementById('domains-list').innerHTML = '<li class="rule-item error">ドメインリストの読み込みに失敗しました。</li>';
    }
}

async function addDomain() {
    const input = document.getElementById('new-domain');
    const domain = input.value.trim();
    if (!domain) { alert('ドメイン名を入力してください。'); return; }
    try {
        const response = await fetch('/api/rules/domains', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domain: domain })
        });
        const result = await response.json();
        if (response.ok) {
            input.value = '';
            loadBlockedDomains();
        } else {
            alert(`エラー: ${result.error || 'ドメインの追加に失敗しました。'}`);
        }
    } catch (error) {
        console.error('Failed to add domain:', error);
        alert('通信エラーが発生しました。');
    }
}

async function deleteDomain(domainToDelete) {
    if (!confirm(`本当にドメイン "${domainToDelete}" をブロックリストから削除しますか？`)) return;
    try {
        const response = await fetch('/api/rules/domains', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domain: domainToDelete })
        });
        const result = await response.json();
        if (response.ok) {
            loadBlockedDomains();
        } else {
            alert(`エラー: ${result.error || 'ドメインの削除に失敗しました。'}`);
        }
    } catch (error) {
        console.error('Failed to delete domain:', error);
        alert('通信エラーが発生しました。');
    }
}

// --- フィルタリング有効/無効 ---
async function loadFilteringStatus() {
    console.log("Loading filtering status...");
    try {
        const response = await fetch('/api/filtering/status');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        const toggle = document.getElementById('filtering-toggle');
        toggle.checked = data.is_enabled;
    } catch (error) {
        console.error('Failed to load filtering status:', error);
        alert('フィルタリング状態の読み込みに失敗しました。');
    }
}

async function toggleFiltering() {
    const toggle = document.getElementById('filtering-toggle');
    const newState = toggle.checked;
    console.log(`Setting filtering to: ${newState}`);
    try {
        const response = await fetch('/api/filtering/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_enabled: newState })
        });
        const result = await response.json();
        if (!response.ok) {
            alert(`エラー: ${result.error || '状態の変更に失敗しました。'}`);
            toggle.checked = !newState;
        }
    } catch (error) {
        console.error('Failed to toggle filtering:', error);
        alert('通信エラーによりフィルタリング状態の変更に失敗しました。');
        toggle.checked = !newState;
    }
}

// =============================================================================
// ダッシュボード・通信監視機能
// =============================================================================
function initializeDashboard() {
    // 最初にページを開いたときに一度だけログを読み込む
    refreshTrafficLogs();
}

async function refreshTrafficLogs() {
    console.log("Refreshing traffic logs...");
    try {
        const response = await fetch('/api/logs?per_page=100');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        const tbody = document.getElementById('traffic-tbody');
        tbody.innerHTML = '';
        if (data.logs.length === 0) {
             tbody.innerHTML = '<tr><td colspan="7" class="empty">まだログはありません。「更新」ボタンを押して再取得してください。</td></tr>';
             return;
        }
        data.logs.forEach(log => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(log.timestamp).toLocaleTimeString('ja-JP')}</td>
                <td>${log.client_ip}</td>
                <td>${log.method}</td>
                <td class="url-cell" title="${log.url}">${log.url}</td>
                <td>${log.status_code}</td>
                <td class="${log.is_blocked ? 'blocked' : 'allowed'}">${log.is_blocked ? 'はい' : 'いいえ'}</td>
                <td><button class="btn btn-sm" onclick='showDetailModal(${JSON.stringify(log)})'>詳細</button></td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Failed to refresh traffic logs:', error);
        document.getElementById('traffic-tbody').innerHTML = `<tr><td colspan="7" class="error">ログの読み込みに失敗しました。プロキシが起動しているか確認してください。</td></tr>`;
    }
}

/**
 * 詳細表示モーダルにログ情報を表示する
 * @param {object} log - テーブル行に対応するログオブジェクト
 */
function showDetailModal(log) {
    const formattedLog = JSON.stringify(log, null, 2); 
    document.getElementById('detail-content').innerHTML = `<pre>${formattedLog}</pre>`;
    document.getElementById('detail-modal').style.display = 'block';
}

/**
 * 詳細表示モーダルを閉じる
 */
function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

function downloadCertificate() {
    window.open('http://mitm.it', '_blank');
}