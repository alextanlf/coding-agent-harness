// web/static/app.js
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
    const resp = await fetch('/api/credentials');
    const data = await resp.json();
    document.getElementById('cred-status').textContent =
        data.configured ? 'API key configured.' : 'No API key configured.';
    document.getElementById('credential-banner').classList.toggle('hidden', data.configured);
}

async function submitTask() {
    const input = document.getElementById('task-input');
    const task = input.value.trim();
    if (!task) return;
    input.value = '';
    addLogEntry('task', `Task: ${task}`);
    const resp = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
    });
    const data = await resp.json();
    currentSessionId = data.session_id;
    connectWebSocket(currentSessionId);
}

function connectWebSocket(sessionId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/session/${sessionId}`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
    };
    ws.onclose = () => {
        addLogEntry('info', 'Session ended.');
    };
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'action':
            addLogEntry('action', `${msg.data.action_type}: ${msg.data.path || msg.data.command || ''}`);
            break;
        case 'blocked':
            addLogEntry('blocked', `Blocked: ${msg.data.reason}`);
            break;
        case 'hitl_request':
            showHITLCard(msg.data);
            break;
        case 'test_result':
            addLogEntry('test', `Tests ${msg.data.passed ? 'passed' : 'failed'}`);
            break;
        case 'complete':
            addLogEntry('complete', `Task ${msg.data.success ? 'completed' : 'failed'} (${msg.data.iterations} iterations)`);
            break;
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

function showHITLCard(data) {
    const log = document.getElementById('action-log');
    const card = document.createElement('div');
    card.className = 'hitl-card';
    card.innerHTML = `<p>Approval needed: ${data.action} — ${data.reason}</p>`;
    const approveBtn = document.createElement('button');
    approveBtn.textContent = 'Approve';
    approveBtn.onclick = () => resolveHITL(data.request_id, 'approve');
    const denyBtn = document.createElement('button');
    denyBtn.textContent = 'Deny';
    denyBtn.onclick = () => resolveHITL(data.request_id, 'deny');
    card.appendChild(approveBtn);
    card.appendChild(denyBtn);
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
}

async function resolveHITL(requestId, decision) {
    await fetch(`/api/session/${currentSessionId}/${decision}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId }),
    });
}

async function saveCredentials() {
    const masterPassword = document.getElementById('master-password').value;
    const apiKey = document.getElementById('api-key').value;
    if (!masterPassword || !apiKey) return;
    await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ master_password: masterPassword, api_key: apiKey }),
    });
    document.getElementById('master-password').value = '';
    document.getElementById('api-key').value = '';
    checkCredStatus();
}

async function clearCredentials() {
    await fetch('/api/credentials', { method: 'DELETE' });
    checkCredStatus();
}

checkCredStatus();
