let ws = null;
let isConnecting = false;

function connectWebSocket() {
    if (ws !== null || isConnecting) return;

    isConnecting = true;
    ws = new WebSocket(`ws://${window.location.host}/ws`);

    ws.onopen = () => {
        console.log('Connected to WebSocket');
        isConnecting = false;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed');
        ws = null;
        isConnecting = false;
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws = null;
        isConnecting = false;
    };
}

function handleMessage(data) {
    const typingIndicator = document.getElementById('typing-indicator');
    typingIndicator.style.display = 'none';

    if (data.type === 'error') {
        appendMessage('bot', `Error: ${data.content}`);
    } else if (data.type === 'tool_call') {
        appendToolCall(data.content);
    } else {
        appendMessage('bot', formatResponse(data.content));
    }

    scrollToBottom();
}

function formatResponse(response) {
    if (typeof response === 'object') {
        if (response.sql) {
            let formatted = `SQL Query: ${response.sql}\n\n`;
            if (response.results) {
                formatted += `Results: ${JSON.stringify(response.results, null, 2)}`;
            }
            return formatted;
        }
        return JSON.stringify(response, null, 2);
    }
    return response;
}

function appendMessage(sender, text) {
    const messages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = text;
    messages.appendChild(messageDiv);
}

function appendToolCall(toolCall) {
    const messages = document.getElementById('chat-messages');
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-call';
    toolDiv.textContent = `Tool Call: ${JSON.stringify(toolCall, null, 2)}`;
    messages.appendChild(toolDiv);
}

function scrollToBottom() {
    const messages = document.getElementById('chat-messages');
    messages.scrollTop = messages.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        appendMessage('user', message);
        ws.send(message);
        
        input.value = '';
        
        const typingIndicator = document.getElementById('typing-indicator');
        typingIndicator.style.display = 'block';
        
        scrollToBottom();
    }
}

// Connect when the page loads
document.addEventListener('DOMContentLoaded', connectWebSocket);

// Add event listener for Enter key
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
