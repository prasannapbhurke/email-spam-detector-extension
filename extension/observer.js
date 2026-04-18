let observerStarted = false;
let inboxScanScheduled = false;
let lastOpenedEmailKey = "";

function startObserving() {
    if (observerStarted) {
        return;
    }
    observerStarted = true;

    scheduleInboxScan(true);

    const observer = new MutationObserver(() => {
        scheduleInboxScan(false);
        scheduleOpenedEmailCheck();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    window.addEventListener("scroll", () => scheduleInboxScan(false), { passive: true });
}

function isRowVisible(row) {
    const rect = row.getBoundingClientRect();
    return rect.bottom >= -40 && rect.top <= window.innerHeight + 120;
}

function getRowKey(row, sender, subject, snippet) {
    return row.id || `${sender}::${subject}::${snippet}`.trim();
}

function scheduleInboxScan(forceAll) {
    if (inboxScanScheduled) {
        return;
    }

    inboxScanScheduled = true;
    setTimeout(() => {
        inboxScanScheduled = false;
        const rows = Array.from(document.querySelectorAll('tr[role="row"]'));

        rows.forEach((row, index) => {
            const sender = row.querySelector('.zF')?.getAttribute('email') ||
                row.querySelector('.bA4')?.innerText || "";
            const subject = row.querySelector('.bog')?.innerText || "";
            const snippet = row.querySelector('.y2')?.innerText || "";
            const rowKey = getRowKey(row, sender, subject, snippet);

            if (!rowKey.trim()) {
                return;
            }

            if (row.dataset.badgeKey !== rowKey) {
                row.dataset.analysisStarted = "";
                row.dataset.badgeKey = rowKey;
            }

            const shouldProcess = forceAll || index < 15 || isRowVisible(row);
            if (shouldProcess) {
                processEmailRow(row, sender, subject, snippet, rowKey);
            }
        });
    }, 120);
}

function scheduleOpenedEmailCheck() {
    requestAnimationFrame(() => {
        const currentHash = window.location.hash;
        const bodySelectors = ['.ii.gt', '.a3s.aiL', '.ads', '[role="main"] .adP'];
        let activeBody = null;

        for (const selector of bodySelectors) {
            const element = document.querySelector(selector);
            if (element && element.offsetHeight > 0 && element.innerText.trim().length > 40) {
                activeBody = element;
                break;
            }
        }

        if (!activeBody) {
            return;
        }

        const subject = document.querySelector('h2.hP')?.innerText || "Email Analysis";
        const bodyText = activeBody.innerText.trim();
        const emailKey = `${currentHash}::${subject}::${bodyText.slice(0, 120)}`;

        if (emailKey !== lastOpenedEmailKey) {
            lastOpenedEmailKey = emailKey;
            processOpenedEmail(activeBody, subject, bodyText, currentHash);
        }
    });
}

async function processEmailRow(row, sender, subject, snippet, rowKey) {
    if (row.querySelector(".spam-badge") && row.dataset.analysisKey === rowKey) {
        return;
    }

    if (row.dataset.analysisStarted === "true" &&
        row.dataset.analysisKey === rowKey &&
        row.dataset.analysisInFlight === "true") {
        return;
    }

    row.dataset.analysisStarted = "true";
    row.dataset.analysisKey = rowKey;
    row.dataset.analysisInFlight = "true";

    const data = await getEmailAnalysis({
        id: rowKey,
        subject,
        sender,
        snippet,
        analysisMode: "preview"
    });

    if (!data) {
        row.dataset.analysisInFlight = "";
        return;
    }

    const existingBadge = row.querySelector(".spam-badge");
    if (existingBadge) {
        existingBadge.remove();
    }

    injectBadgeToRow(row, data);
    row.dataset.analysisInFlight = "";
}

async function processOpenedEmail(container, subject, bodyText, hash) {
    const emailObj = {
        id: hash,
        subject,
        body: bodyText,
        analysisMode: "full"
    };

    const data = await getEmailAnalysis(emailObj);
    if (!data) {
        return;
    }

    const headerSelectors = ['.gE.iv.gt', '.acZ', '.hx', '.h7', '.ha', '.iH'];
    let injectionTarget = container;

    for (const selector of headerSelectors) {
        const header = document.querySelector(selector);
        if (header && header.offsetHeight > 0) {
            injectionTarget = header;
            break;
        }
    }

    injectTopPanel(injectionTarget, data, emailObj);
}
