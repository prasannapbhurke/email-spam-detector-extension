function formatQuarantineTime(isoString) {
    if (!isoString) {
        return "Unknown time";
    }

    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
        return "Unknown time";
    }

    return date.toLocaleString();
}

async function checkBackend() {
    const statusEl = document.getElementById("backend-status");
    try {
        const response = await fetch("https://web-production-edebc.up.railway.app/", {
            method: "GET"
        });
        if (response.ok) {
            statusEl.textContent = "Online";
            statusEl.style.color = "#188038";
        } else {
            statusEl.textContent = "Error";
            statusEl.style.color = "#d93025";
        }
    } catch (error) {
        statusEl.textContent = "Offline";
        statusEl.style.color = "#d93025";
    }
}

async function getQuarantineItems() {
    const stored = await chrome.storage.local.get(["quarantineItems"]);
    return Array.isArray(stored.quarantineItems) ? stored.quarantineItems : [];
}

async function removeQuarantineItem(signature) {
    const stored = await chrome.storage.local.get(["quarantinedEmails", "quarantineItems"]);
    const quarantinedEmails = Array.isArray(stored.quarantinedEmails) ? stored.quarantinedEmails : [];
    const quarantineItems = Array.isArray(stored.quarantineItems) ? stored.quarantineItems : [];

    await chrome.storage.local.set({
        quarantinedEmails: quarantinedEmails.filter((item) => item !== signature),
        quarantineItems: quarantineItems.filter((item) => item.signature !== signature)
    });
}

async function clearAllQuarantine() {
    await chrome.storage.local.set({
        quarantinedEmails: [],
        quarantineItems: []
    });
}

async function renderQuarantineList() {
    const container = document.getElementById("quarantine-container");
    const items = await getQuarantineItems();

    if (!items.length) {
        container.innerHTML = `<div class="empty-state">No quarantined emails yet.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="quarantine-list">
            ${items.map((item) => `
                <div class="quarantine-item" data-signature="${item.signature}">
                    <div class="quarantine-item-title">${item.subject || "No subject"}</div>
                    <div class="quarantine-item-preview">${item.preview || "No preview available."}</div>
                    <div class="quarantine-item-meta">Quarantined: ${formatQuarantineTime(item.quarantinedAt)}</div>
                    <div class="quarantine-actions">
                        <button class="btn btn-clear" data-action="remove" data-signature="${item.signature}" type="button">Remove Hide</button>
                    </div>
                </div>
            `).join("")}
        </div>
    `;

    container.querySelectorAll("[data-action='remove']").forEach((button) => {
        button.addEventListener("click", async () => {
            const signature = button.getAttribute("data-signature");
            await removeQuarantineItem(signature);
            await renderQuarantineList();
        });
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    await checkBackend();
    await renderQuarantineList();

    document.getElementById("clear-all-btn").addEventListener("click", async () => {
        await clearAllQuarantine();
        await renderQuarantineList();
    });
});
