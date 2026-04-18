const intersectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const row = entry.target;
            processEmailRow(row);
            intersectionObserver.unobserve(row);
        }
    });
}, { threshold: 0.1 });

function startObservingInbox() {
    const observer = new MutationObserver((mutations) => {
        const rows = document.querySelectorAll('tr[role="row"]');
        rows.forEach(row => {
            if (!row.dataset.observed) {
                row.dataset.observed = "true";
                intersectionObserver.observe(row);
            }
        });

        const emailBodyContainer = document.querySelector('.ii.gt');
        if (emailBodyContainer && !emailBodyContainer.dataset.processed) {
            processOpenedEmail(emailBodyContainer);
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
    container.dataset.processed = "true";

    const bodyText = container.innerText;
    const subject = document.querySelector('h2.hP')?.innerText || "";
    const id = window.location.hash;

    const emailObj = { id, subject, body: bodyText };
    const data = await getEmailAnalysis(emailObj);
    if (data) {
        const topContainer = document.querySelector('.gE.iv.gt') || container.parentElement;
        // Pass the whole email object so feedback has the text
        injectTopPanel(topContainer, data, emailObj);
    }
}

startObservingInbox();
