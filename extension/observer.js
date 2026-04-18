const intersectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            processEmailRow(entry.target);
            intersectionObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

let observerStarted = false;

function startObserving() {
    if (observerStarted) {
        return;
    }
    observerStarted = true;

    const observer = new MutationObserver(() => {
        // 1. Process Inbox Rows
        const rows = document.querySelectorAll('tr[role="row"]');
        rows.forEach(row => {
            if (!row.dataset.observed) {
                row.dataset.observed = "true";
                intersectionObserver.observe(row);
            }
        });

        // 2. Detect Opened Email (Improved for Single Page App transitions)
        const currentHash = window.location.hash;
        const bodySelectors = ['.ii.gt', '.a3s.aiL', '.ads', '[role="main"] .adP'];
        let activeBody = null;

        for (const selector of bodySelectors) {
            const el = document.querySelector(selector);
            if (el && el.offsetHeight > 0 && el.innerText.length > 20) {
                activeBody = el;
                break;
            }
        }

        if (activeBody) {
            // Check if we've switched emails or haven't processed this one yet
            if (activeBody.getAttribute('data-last-hash') !== currentHash) {
                activeBody.setAttribute('data-last-hash', currentHash);
                processOpenedEmail(activeBody);
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
}

async function processEmailRow(row) {
    const sender = row.querySelector('.zF')?.getAttribute('email') ||
                   row.querySelector('.bA4')?.innerText || "";
    const subject = row.querySelector('.bog')?.innerText || "";
    const snippet = row.querySelector('.y2')?.innerText || "";
    const id = row.id || subject + sender;

    const data = await getEmailAnalysis({ id, subject, sender, snippet });
    if (data) {
        injectBadgeToRow(row, data);
    }
}

async function processOpenedEmail(container) {
    const bodyText = container.innerText;
    const subject = document.querySelector('h2.hP')?.innerText || "Email Analysis";
    const id = window.location.hash;

    const emailObj = { id, subject, body: bodyText };
    const data = await getEmailAnalysis(emailObj);

    if (data) {
        // Search for Gmail headers where we can dock the panel
        const headerSelectors = ['.gE.iv.gt', '.acZ', '.hx', '.h7', '.ha', '.iH'];
        let injectionTarget = container;

        for (const sel of headerSelectors) {
            const header = document.querySelector(sel);
            if (header && header.offsetHeight > 0) {
                injectionTarget = header;
                break;
            }
        }

        injectTopPanel(injectionTarget, data, emailObj);
    }
}
