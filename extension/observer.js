const intersectionObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            processEmailRow(entry.target);
            intersectionObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.15, rootMargin: "120px 0px" });

let observerStarted = false;
let inboxScanScheduled = false;
let lastOpenedEmailKey = "";

function startObserving() {
    if (observerStarted) {
        return;
    }
    observerStarted = true;

    scheduleInboxScan();

    const observer = new MutationObserver(() => {
        scheduleInboxScan();
        scheduleOpenedEmailCheck();
    });

    observer.observe(document.body, { childList: true, subtree: true });
}

function scheduleInboxScan() {
    if (inboxScanScheduled) {
        return;
    }

    inboxScanScheduled = true;
    setTimeout(() => {
        inboxScanScheduled = false;
        const rows = document.querySelectorAll('tr[role="row"]');
        rows.forEach((row) => {
            if (!row.dataset.observed) {
                row.dataset.observed = "true";
                intersectionObserver.observe(row);
            }
        });
    }, 250);
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

async function processEmailRow(row) {
    if (row.dataset.analysisStarted === "true") {
        return;
    }

    const sender = row.querySelector('.zF')?.getAttribute('email') ||
                   row.querySelector('.bA4')?.innerText || "";
    const subject = row.querySelector('.bog')?.innerText || "";
    const snippet = row.querySelector('.y2')?.innerText || "";

    row.dataset.analysisStarted = "true";

    const data = await getEmailAnalysis({
        id: row.id || subject + sender,
        subject,
        sender,
        snippet,
        analysisMode: "preview"
    });

    if (data) {
        injectBadgeToRow(row, data);
    }
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
