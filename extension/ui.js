/**
 * Gmail Spam Detector UI Engine (XAI Enhanced + Feedback)
 */

const UI = {
    getThreatLevel(data) {
        if (!data.isSpam) return { badgeLevel: "safe", badgeText: "Safe", panelClass: "safe", panelLabel: "Safe Email", panelAccent: "Normal Risk" };
        if (data.confidence >= 0.95) return { badgeLevel: "critical", badgeText: "Scam", panelClass: "critical", panelLabel: "High Risk Scam", panelAccent: "Immediate Caution" };
        return { badgeLevel: "high", badgeText: "Spam", panelClass: "warning", panelLabel: "Spam Warning", panelAccent: "Review Suggested" };
    },

    createBadge(data) {
        const badge = document.createElement("span");
        const threat = this.getThreatLevel(data);
        badge.className = `spam-badge ${threat.badgeLevel}`;
        badge.textContent = `${threat.badgeText} ${Math.round(data.confidence * 100)}%`;
        badge.dataset.explanation = data.explanation;
        badge.dataset.tech = data.technicalExplanation || "";
        badge.addEventListener("mouseenter", (e) => this.showTooltip(e));
        badge.addEventListener("mouseleave", () => this.hideTooltip());
        return badge;
    },

    showTooltip(event) {
        this.hideTooltip();
        const tooltip = document.createElement("div");
        tooltip.id = "spam-tooltip-active";
        tooltip.className = "spam-tooltip";
        tooltip.innerHTML = `<strong>AI Analysis</strong><div>${event.target.dataset.explanation}</div><div style="margin-top: 8px; font-size: 10px; color: #666; border-top: 1px solid #ddd; padding-top: 5px;">${event.target.dataset.tech}</div>`;
        document.body.appendChild(tooltip);
        const rect = event.target.getBoundingClientRect();
        tooltip.style.left = `${rect.left}px`;
        tooltip.style.top = `${rect.bottom + 5 + window.scrollY}px`;
    },

    hideTooltip() {
        const existing = document.getElementById("spam-tooltip-active");
        if (existing) existing.remove();
    },

    injectFloatingPanel(container, data, emailObj) {
        // Prevent duplicate panels
        if (document.getElementById("spam-floating-panel")) {
            document.getElementById("spam-floating-panel").remove();
        }

        const panel = document.createElement("div");
        const threat = this.getThreatLevel(data);
        const keywords = Array.isArray(data.contributingKeywords) ? data.contributingKeywords : [];
        panel.id = "spam-floating-panel";
        panel.className = `spam-panel-floating ${threat.panelClass}`;

        panel.innerHTML = `
            <div class="spam-panel-header">
                <div><div class="spam-panel-kicker">${threat.panelAccent}</div><div class="spam-panel-title">${threat.panelLabel}</div></div>
                <div class="spam-panel-score">${Math.round(data.confidence * 100)}%</div>
            </div>
            <div class="spam-panel-explanation">
                <strong>Analysis:</strong> ${data.explanation}
                ${keywords.length > 0 ? `<div class="kw-tag-list">${keywords.map(k => `<span class="kw-tag">${k.word}</span>`).join("")}</div>` : ""}
            </div>
            <div class="spam-panel-actions">
                <button class="spam-btn spam-btn-safe" id="btn-mark-safe">Mark as Safe</button>
                <button class="spam-btn spam-btn-report" id="btn-report-spam">Report Spam</button>
            </div>`;

        // Gmail's dynamic loading can be tricky. Try to prepend to container, if fails, append to body
        try {
            container.prepend(panel);
        } catch (e) {
            document.body.appendChild(panel);
            panel.style.position = 'fixed';
            panel.style.top = '100px';
            panel.style.right = '20px';
            panel.style.zIndex = '9999';
        }

        panel.querySelector("#btn-mark-safe").onclick = () => {
            sendFeedback(emailObj, false);
            this.clearHighlights();
            panel.remove();
        };

        panel.querySelector("#btn-report-spam").onclick = () => {
            sendFeedback(emailObj, true);
            panel.remove();
        };

        if (data.isSpam && keywords.length > 0) this.highlightKeywords(keywords.map(k => k.word));
    },

    highlightKeywords(keywords) {
        const body = document.querySelector('.ii.gt') || document.querySelector('.a3s.aiL');
        if (!body) return;
        let html = body.innerHTML;
        keywords.forEach(kw => {
            const regex = new RegExp(`\\b(${kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`, "gi");
            html = html.replace(regex, '<span class="spam-highlight-text">$1</span>');
        });
        body.innerHTML = html;
    },

    clearHighlights() {
        document.querySelectorAll(".spam-highlight-text").forEach(el => el.replaceWith(el.textContent));
    }
};

function injectBadgeToRow(row, data) {
    const cell = row.querySelector(".y6");
    if (cell && !row.querySelector(".spam-badge")) cell.appendChild(UI.createBadge(data));
}

function injectTopPanel(container, data, emailObj) {
    UI.injectFloatingPanel(container, data, emailObj);
}
