const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

let requestQueue = Promise.resolve();
const analysisCache = new Map();
const MAX_CACHE_SIZE = 300;
const LOCAL_SPAM_PATTERNS = [
    { pattern: /\blottery\b/i, score: 22, reason: "Lottery claim language detected." },
    { pattern: /\bclaim\b.{0,20}\bprize\b/i, score: 18, reason: "Prize-claim wording detected." },
    { pattern: /\bbank details\b/i, score: 24, reason: "Requests for bank details are high risk." },
    { pattern: /\bid proof\b/i, score: 18, reason: "Sensitive identity document request detected." },
    { pattern: /\bverify\b.{0,20}\baccount\b/i, score: 16, reason: "Account verification wording detected." },
    { pattern: /\burgent\b/i, score: 10, reason: "Urgent pressure language detected." },
    { pattern: /\bwinner\b/i, score: 12, reason: "Winner notification wording detected." },
    { pattern: /\botp\b/i, score: 18, reason: "OTP request detected." },
    { pattern: /\bpassword\b/i, score: 18, reason: "Password-related request detected." },
    { pattern: /\brefund\b/i, score: 10, reason: "Refund lure wording detected." }
];

function getErrorMessage(error) {
    if (error instanceof Error && error.message) {
        return error.message;
    }

    if (typeof error === "string" && error.trim()) {
        return error;
    }

    try {
        return JSON.stringify(error);
    } catch {
        return "Unknown error";
    }
}

async function securePost(endpoint, body) {
    requestQueue = requestQueue.then(async () => {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await fetch(API_BASE_URL + endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                },
                body: JSON.stringify(body),
                signal: controller.signal
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`HTTP ${response.status}: ${text}`);
            }

            return await response.json();
        } catch (error) {
            if (error && error.name === "AbortError") {
                throw new Error("Request timed out");
            }

            if (error instanceof Error) {
                throw error;
            }

            throw new Error("Network error");
        } finally {
            clearTimeout(timeoutId);
        }
    });

    return requestQueue;
}

function getCacheKey(emailText, analysisMode) {
    return `${analysisMode}:${emailText}`;
}

function readCachedAnalysis(emailText, analysisMode) {
    return analysisCache.get(getCacheKey(emailText, analysisMode)) || null;
}

function storeCachedAnalysis(emailText, analysisMode, value) {
    const key = getCacheKey(emailText, analysisMode);
    if (analysisCache.size >= MAX_CACHE_SIZE) {
        const oldestKey = analysisCache.keys().next().value;
        analysisCache.delete(oldestKey);
    }
    analysisCache.set(key, value);
}

function normalizePrediction(result, emailText) {
    const riskScore = Number(result.risk_score) || 0;
    const confidence = typeof result.confidence === "number" ? result.confidence : riskScore / 100;
    const reasons = Array.isArray(result.reasons) ? result.reasons : [];
    const rawKeywords = Array.isArray(result.keywords) ? result.keywords : [];
    const contributingKeywords = rawKeywords.map((keyword) => {
        if (typeof keyword === "string") {
            return { word: keyword, importance: 0.5 };
        }

        return {
            word: keyword.word || "",
            importance: typeof keyword.importance === "number" ? keyword.importance : 0.5
        };
    }).filter((keyword) => keyword.word);

    const intentSummary = reasons.length > 0
        ? reasons.join(" ")
        : (riskScore >= 70 ? "This email shows strong spam or phishing signals." : "No major spam indicators were detected.");

    return {
        label: result.label || "Analyzed",
        risk_score: riskScore,
        confidence,
        reasons,
        keywords: rawKeywords,
        isSpam: riskScore >= 50 || result.label === "Suspicious" || result.label === "Dangerous",
        explanation: intentSummary,
        intentSummary,
        warningMessage: reasons[0] || "",
        suggestedFilter: riskScore >= 70 ? "Move to Spam / Quarantine" : "Keep in Inbox",
        contributingKeywords,
        emailText
    };
}

function getLocalPreviewAnalysis(email) {
    const emailText = `${email.subject || ""} ${email.snippet || ""}`.trim() || "No content";
    const matches = [];
    let score = 8;

    for (const item of LOCAL_SPAM_PATTERNS) {
        if (item.pattern.test(emailText)) {
            score += item.score;
            matches.push(item);
        }
    }

    score = Math.max(5, Math.min(score, 98));
    const isSpam = score >= 45;

    return {
        label: isSpam ? (score >= 75 ? "Dangerous" : "Suspicious") : "Safe",
        risk_score: score,
        confidence: score / 100,
        reasons: matches.slice(0, 2).map((item) => item.reason),
        keywords: matches.slice(0, 4).map((item) => item.reason.replace(/\.$/, "")),
        isSpam,
        explanation: matches.length > 0 ? matches[0].reason : "No major spam indicators were detected.",
        intentSummary: matches.length > 0 ? matches.map((item) => item.reason).join(" ") : "No major spam indicators were detected.",
        warningMessage: matches[0]?.reason || "",
        suggestedFilter: isSpam ? "Review before opening" : "Keep in Inbox",
        contributingKeywords: matches.slice(0, 4).map((item) => ({
            word: item.reason.replace(/\.$/, ""),
            importance: item.score / 100
        })),
        emailText,
        analysisSource: "local-preview",
        previewOnly: true
    };
}

async function getEmailAnalysis(email) {
    const emailText = `${email.subject || ""} ${email.snippet || ""} ${email.body || ""}`.trim() || "No content";
    const analysisMode = email.analysisMode === "preview" ? "preview" : "full";

    if (analysisMode === "preview") {
        return getLocalPreviewAnalysis(email);
    }

    const cached = readCachedAnalysis(emailText, analysisMode);
    if (cached) {
        return cached;
    }

    const payload = {
        email_text: emailText,
        html_content: analysisMode === "full" ? (email.body || "") : "",
        analysis_mode: analysisMode
    };

    try {
        const result = await securePost("/predict", payload);
        const normalized = normalizePrediction(result, emailText);
        storeCachedAnalysis(emailText, analysisMode, normalized);
        return normalized;
    } catch (error) {
        console.error("Spam analysis failed:", getErrorMessage(error), error);
        return null;
    }
}

async function sendFeedback(emailObj, isActuallySpam) {
    const payload = {
        text: `${emailObj.subject || ""} ${emailObj.body || ""}`.trim(),
        prediction: isActuallySpam ? "spam" : "ham",
        isActuallySpam
    };

    try {
        await securePost("/feedback", payload);
    } catch (error) {
        console.error("Feedback submission failed:", getErrorMessage(error), error);
    }
}
