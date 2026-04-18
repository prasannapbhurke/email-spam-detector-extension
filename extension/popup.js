async function checkBackend() {
    const statusEl = document.getElementById('backend-status');
    try {
        const response = await fetch('https://web-production-edebc.up.railway.app/', {
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
