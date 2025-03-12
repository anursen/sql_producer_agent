let ws = new WebSocket(`ws://${window.location.host}/chat/ws`);

ws.onmessage = function(event) {
    appendMessage('bot', event.data);
};

function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (message) {
        appendMessage('user', message);
        ws.send(message);
        input.value = '';
    }
}

function appendMessage(sender, text) {
    const messages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = text;
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}
