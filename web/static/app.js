let currentSessionId = null;
let ws = null;

document.getElementById('submit-btn').addEventListener('click', submitTask);
document.getElementById('task-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') submitTask();
});
document.getElementById('settings-btn').addEventListener('click', () => {
    document.getElementById('settings-modal').classList.remove('hidden');
    checkCredStatus();
});
document.getElementById('close-modal-btn').addEventListener('click', () => {
    document.getElementById('settings-modal').classList.add('hidden');
});
document.getElementById('save-cred-btn').addEventListener('click', saveCredentials);
document.getElementById('clear-cred-btn').addEventListener('click', clearCredentials);
document.getElementById('configure-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('settings-modal').classList.remove('hidden');
    checkCredStatus();
});

async function checkCredStatus() {
    try {
        const resp = await fetch('/api/credentials');
        const data = await resp.json();
        const configured = data.configured;
        document.getElementById('cred-status').textContent =
            configured ? '✅ API key configured.' : '❌ No API key configured.';
        document.getElementById('credential-banner').classList.toggle('hidden', configured);
    } catch (e) {
        document.getElementById('cred-status').textContent = '⚠️ Cannot reach server.';
    }
}

async function submitTask() {
    const input = document.getElementById('task-input');
    const task = input.value.trim();
    if (!task) return;
    input.value = '';
    document.getElementById('submit-btn').disabled = true;

    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('action-log').classList.remove('hidden');

    addLogEntry('task', `📋 Task: ${task}`);

    try {
        const resp = await fetch('/api/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task }),
        });
        if (!resp.ok) {
            addLogEntry('error', `❌ Server error: ${resp.status}`);
            document.getElementById('submit-btn').disabled = false;
            return;
        }
        const data = await resp.json();
        currentSessionId = data.session_id;
        addLogEntry('info', '🔌 Connecting to agent...');
        connectWebSocket(currentSessionId);
    } catch (e) {
        addLogEntry('error', `❌ Network error: ${e.message}`);
        document.getElementById('submit-btn').disabled = false;
    }
}

function connectWebSocket(sessionId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/session/${sessionId}`);

    ws.onopen = () => {
        addLogEntry('info', '✅ Connected. Agent is working...');
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
    };

    ws.onclose = () => {
        document.getElementById('submit-btn').disabled = false;
    };

    ws.onerror = () => {
        addLogEntry('error', '❌ WebSocket connection failed.');
        document.getElementById('submit-btn').disabled = false;
    };
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'action':
            const detail = msg.data.path || msg.data.command || '';
            const icons = { read_file: '📖', write_file: '✏️', list_files: '📂', run_shell: '⚡', run_tests: '🧪' };
            addLogEntry('action', `${icons[msg.data.action_type] || '🔧'} ${msg.data.action_type}${detail ? ': ' + detail : ''}`);
            break;
        case 'blocked':
            addLogEntry('blocked', `🚫 Blocked: ${msg.data.reason}`);
            break;
        case 'hitl_request':
            showHITLCard(msg);
            break;
        case 'test_result':
            if (msg.data.passed) {
                addLogEntry('test', '✅ All tests passed!');
            } else {
                const failures = msg.data.failures.map(f => `  • ${f.name}: ${f.message}`).join('\n');
                addLogEntry('test', `❌ Tests failed:\n${failures}`);
            }
            break;
        case 'complete':
            if (msg.success) {
                addLogEntry('complete', `✅ Task completed in ${msg.iterations} iteration(s).`);
            } else {
                addLogEntry('error', `❌ Task failed: ${msg.reason} (${msg.iterations} iterations)`);
            }
            break;
        case 'parse_error':
            addLogEntry('error', `⚠️ Parse error: ${msg.data?.error || 'unknown'}`);
            break;
        case 'error':
            addLogEntry('error', `❌ ${msg.message || msg.data?.message || 'Unknown error'}`);
            break;
        default:
            addLogEntry('info', JSON.stringify(msg));
    }
}

function addLogEntry(type, text) {
    const log = document.getElementById('action-log');
    const entry = document.createElement('div');
    entry.className = `action-entry ${type}`;
    entry.textContent = text;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function showHITLCard(msg) {
    const log = document.getElementById('action-log');
    const card = document.createElement('div');
    card.className = 'hitl-card';
    const action = msg.action || msg.data?.action || 'unknown';
    const command = msg.command || msg.data?.command || '';
    const reason = msg.reason || msg.data?.reason || '';
    card.innerHTML = `<p>🔐 <b>Approval needed</b><br>${action}${command ? ': ' + command : ''}<br><small>${reason}</small></p>`;
    const approveBtn = document.createElement('button');
    approveBtn.textContent = '✅ Approve';
    approveBtn.className = 'approve-btn';
    approveBtn.onclick = () => {
        approveBtn.disabled = true;
        denyBtn.disabled = true;
        resolveHITL(msg.request_id || msg.data?.request_id, 'approve');
        card.innerHTML = '<p>✅ Approved</p>';
    };
    const denyBtn = document.createElement('button');
    denyBtn.textContent = '❌ Deny';
    denyBtn.className = 'deny-btn';
    denyBtn.onclick = () => {
        approveBtn.disabled = true;
        denyBtn.disabled = true;
        resolveHITL(msg.request_id || msg.data?.request_id, 'deny');
        card.innerHTML = '<p>❌ Denied</p>';
    };
    card.appendChild(approveBtn);
    card.appendChild(denyBtn);
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
}

async function resolveHITL(requestId, decision) {
    try {
        await fetch(`/api/session/${currentSessionId}/${decision}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId }),
        });
    } catch (e) {
        addLogEntry('error', `Failed to send ${decision}: ${e.message}`);
    }
}

async function saveCredentials() {
    const masterPassword = document.getElementById('master-password').value;
    const apiKey = document.getElementById('api-key').value;
    if (!masterPassword || !apiKey) {
        document.getElementById('cred-status').textContent = '⚠️ Both fields are required.';
        return;
    }
    document.getElementById('save-cred-btn').disabled = true;
    document.getElementById('save-cred-btn').textContent = 'Saving...';
    try {
        await fetch('/api/credentials', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_password: masterPassword, api_key: apiKey }),
        });
        document.getElementById('master-password').value = '';
        document.getElementById('api-key').value = '';
        await checkCredStatus();
    } catch (e) {
        document.getElementById('cred-status').textContent = `❌ Error: ${e.message}`;
    }
    document.getElementById('save-cred-btn').disabled = false;
    document.getElementById('save-cred-btn').textContent = 'Save';
}

async function clearCredentials() {
    try {
        await fetch('/api/credentials', { method: 'DELETE' });
        await checkCredStatus();
    } catch (e) {
        document.getElementById('cred-status').textContent = `❌ Error: ${e.message}`;
    }
}

checkCredStatus();
