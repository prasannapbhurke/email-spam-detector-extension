async function checkBackend() {
    const statusEl = document.getElementById('backend-status');
    try {
        const response = await fetch('http://127.0.0.1:8002/health', {
            method: 'GET'
        });
        if (response.ok) {
            statusEl.textContent = "Online";
            statusEl.style.color = "#188038";
        } else {
            statusEl.textContent = "Error";
            statusEl.style.color = "#d93025";
        }
    } catch (e) {
        statusEl.textContent = "Offline";
        statusEl.style.color = "#d93025";
    }
}

document.addEventListener('DOMContentLoaded', checkBackend);
