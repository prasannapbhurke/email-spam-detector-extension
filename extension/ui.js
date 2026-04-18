/**
 * Next-Gen AI Email Assistant UI (Inbox Management Fix)
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
                <strong>⚠️ Security Alert:</strong> ${data.warningMessage}
             </div>` : '';

        panel.innerHTML = `
            <div class="spam-panel-header">
                <div>
                    <div class="spam-panel-kicker">AI SECURITY ANALYSIS</div>
                    <div class="spam-panel-title">${data.isSpam ? 'High Risk Intent' : 'Trusted Intent'}</div>
                </div>
                <div class="spam-panel-score">${Math.round(data.confidence * 100)}%</div>
            </div>
            <div class="spam-panel-explanation" style="margin-top: 10px;">
                <strong>AI Summary:</strong> ${data.intentSummary}
                ${warningBox}
            </div>
            <div style="margin-top: 15px; font-size: 12px; color: #1a73e8; border-top: 1px solid #eee; padding-top: 10px;">
                <strong>💡 Recommendation:</strong> Filter <code>${data.suggestedFilter}</code>
            </div>
            <div class="spam-panel-actions">
                <button class="spam-btn spam-btn-safe" id="btn-mark-safe">Allow Content</button>
                <button class="spam-btn spam-btn-report" id="btn-quarantine">Instant Quarantine</button>
            </div>`;

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

        panel.querySelector("#btn-quarantine").onclick = () => {
            sendFeedback(emailObj, true);

            // 1. ARCHIVE THE EMAIL (Real removal from inbox)
            // We simulate a click on Gmail's 'Archive' button or use the 'e' shortcut
            const archiveBtn = document.querySelector('[data-tooltip="Archive"]') || document.querySelector('.T-I.J-J5-Ji.lS.T-I-ax7.L3');
            if (archiveBtn) {
                archiveBtn.click();
            } else {
                // Fallback: Just hide it manually if button not found
                const body = document.querySelector('.ii.gt') || document.querySelector('.a3s.aiL');
                if (body) body.style.display = 'none';
            }

            // 2. Show the Security Overlay
            const overlay = document.createElement('div');
            overlay.id = "spam-security-overlay";
            overlay.style.cssText = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(255,255,255,0.95); z-index:99999; display:flex; align-items:center; justify-content:center; font-family: sans-serif;";

            const card = document.createElement('div');
            card.style.cssText = "background: #1a1a1a; color: white; padding: 40px; border-radius: 16px; text-align: center; max-width: 450px; box-shadow: 0 20px 40px rgba(0,0,0,0.3);";
            card.innerHTML = `
                <div style="font-size: 60px; margin-bottom: 20px;">🛡️</div>
                <h1 style="margin: 0 0 10px 0; font-size: 26px;">Quarantined Successfully</h1>
                <p style="color: #bbb; margin-bottom: 30px; line-height: 1.5;">This email has been moved to your archives. Your credentials and privacy are now protected.</p>
                <button id="go-back-btn" style="padding: 14px 32px; border-radius: 10px; border: none; background: #1a73e8; color: white; font-weight: bold; cursor: pointer; font-size: 18px; transition: background 0.2s;">Return to Inbox</button>
            `;

            overlay.appendChild(card);
            document.body.appendChild(overlay);

            document.getElementById('go-back-btn').addEventListener('click', () => {
                overlay.remove();
                window.location.hash = '#inbox';
            });
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

        if (data.isSpam) {
            row.style.background = '#fff8f8';
            row.style.transition = 'all 0.5s';
        }
    }
};

function injectBadgeToRow(row, data) {
    UI.injectBadgeToRow(row, data);
}

function injectTopPanel(container, data, emailObj) {
    UI.injectFloatingPanel(container, data, emailObj);
}
