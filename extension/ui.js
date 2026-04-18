/**
 * Next-Gen AI Email Assistant UI
 */

const UI = {
    injectFloatingPanel(container, data, emailObj) {
        if (document.getElementById("spam-floating-panel")) {
            document.getElementById("spam-floating-panel").remove();
        }

        const panel = document.createElement("div");
        panel.id = "spam-floating-panel";
        panel.className = `spam-panel-floating ${data.isSpam ? 'warning' : 'safe'}`;

        const warningBox = data.warningMessage ?
            `<div style="background: #fff3cd; color: #856404; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #ffeeba; font-size: 13px;">
                <strong>⚠️ Warning:</strong> ${data.warningMessage}
             </div>` : '';

        panel.innerHTML = `
            <div class="spam-panel-header">
                <div>
                    <div class="spam-panel-kicker">AI INTENT ANALYSIS</div>
                    <div class="spam-panel-title">${data.isSpam ? 'Suspicious Intent' : 'Trusted Intent'}</div>
                </div>
                <div class="spam-panel-score">${Math.round(data.confidence * 100)}%</div>
            </div>
            <div class="spam-panel-explanation" style="margin-top: 10px;">
                <strong>Summary:</strong> ${data.intentSummary}
                ${warningBox}
            </div>
            <div style="margin-top: 15px; font-size: 12px; color: #1a73e8; border-top: 1px solid #eee; padding-top: 10px;">
                <strong>💡 Smart Filter:</strong> Blocks <code>${data.suggestedFilter}</code>
            </div>
            <div class="spam-panel-actions">
                <button class="spam-btn spam-btn-safe" id="btn-mark-safe">Mark as Safe</button>
                <button class="spam-btn spam-btn-report" id="btn-auto-hide">Auto-Hide Email</button>
            </div>`;

        // Handle dynamic Gmail injection
        if (container.prepend) {
            container.prepend(panel);
        } else {
            document.body.appendChild(panel);
        }

        panel.querySelector("#btn-mark-safe").onclick = () => {
            sendFeedback(emailObj, false);
            this.clearHighlights();
            panel.remove();
        };

        panel.querySelector("#btn-auto-hide").onclick = () => {
            sendFeedback(emailObj, true);
            const body = document.querySelector('.ii.gt') || document.querySelector('.a3s.aiL');
            if (body) {
                body.style.filter = 'blur(15px)';
                body.style.pointerEvents = 'none';
                body.style.userSelect = 'none';
            }
            panel.innerHTML = "<div style='padding: 20px; text-align: center; font-weight: bold;'>🛡️ Content hidden for your safety.</div>";
        };

        if (data.isSpam && data.contributingKeywords) {
            this.highlightKeywords(data.contributingKeywords.map(k => k.word));
        }
    },

    highlightKeywords(keywords) {
        const body = document.querySelector('.ii.gt') || document.querySelector('.a3s.aiL');
        if (!body) return;
        let html = body.innerHTML;
        keywords.forEach(kw => {
            const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            const regex = new RegExp(`\\b(${escaped})\\b`, "gi");
            html = html.replace(regex, '<span class="spam-highlight-text">$1</span>');
        });
        body.innerHTML = html;
    },

    clearHighlights() {
        document.querySelectorAll(".spam-highlight-text").forEach(el => el.replaceWith(el.textContent));
    },

    injectBadgeToRow(row, data) {
        const cell = row.querySelector(".y6");
        if (!cell || row.querySelector(".spam-badge")) return;

        const badge = document.createElement("span");
        badge.className = `spam-badge ${data.isSpam ? 'high' : 'low'}`;
        badge.textContent = data.isSpam ? 'Suspicious' : 'Safe';
        cell.appendChild(badge);

        // Auto-Hide from Inbox view based on preference
        chrome.storage.local.get(['autoHideSpam'], (result) => {
            if (result.autoHideSpam && data.isSpam) {
                row.style.display = 'none'; // Completely clean inbox
            }
        });
    }
};

function injectBadgeToRow(row, data) {
    UI.injectBadgeToRow(row, data);
}

function injectTopPanel(container, data, emailObj) {
    UI.injectFloatingPanel(container, data, emailObj);
}
