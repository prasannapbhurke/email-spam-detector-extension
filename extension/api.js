const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";
const CACHE_VERSION = "v2";

let requestQueue = Promise.resolve();
const analysisCache = new Map();
const MAX_CACHE_SIZE = 300;

const TRUSTED_SENDER_PATTERNS = [
    /@google\.com$/i,
    /@github\.com$/i,
    /@stripe\.com$/i,
    /@railway\.app$/i,
    /@kaggle\.com$/i,
    /@claude\.ai$/i,
    /@anthropic\.com$/i,
    /@microsoft\.com$/i,
    /@nvidia\.com$/i,
    /@heroku\.com$/i
];

const LOCAL_SPAM_PATTERNS = [
    { pattern: /\bcongratulations\b/i, score: 14, reason: "Prize-style congratulations wording detected." },
    { pattern: /\byou won\b/i, score: 26, reason: "Winning-claim wording detected." },
    { pattern: /[\u20B9₹]\s?\d[\d,]*/i, score: 24, reason: "Large money prize amount detected." },
    { pattern: /\bselected as a winner\b/i, score: 24, reason: "Winner selection wording detected." },
    { pattern: /\binternational lottery\b/i, score: 28, reason: "Lottery scam wording detected." },
    { pattern: /\blottery\b/i, score: 22, reason: "Lottery claim language detected." },
    { pattern: /\bclaim\b.{0,20}\bprize\b/i, score: 18, reason: "Prize-claim wording detected." },
    { pattern: /\bbank details\b/i, score: 24, reason: "Requests for bank details are high risk." },
    { pattern: /\bid proof\b/i, score: 18, reason: "Sensitive identity document request detected." },
    { pattern: /\bpayment details\b/i, score: 18, reason: "Payment detail request detected." },
    { pattern: /\bverify\b.{0,20}\baccount\b/i, score: 16, reason: "Account verification wording detected." },
    { pattern: /\burgent\b/i, score: 10, reason: "Urgent pressure language detected." },
    { pattern: /\bwinner\b/i, score: 12, reason: "Winner notification wording detected." },
    { pattern: /\botp\b/i, score: 18, reason: "OTP request detected." },
    { pattern: /\bpassword\b/i, score: 18, reason: "Password-related request detected." },
    { pattern: /\brefund\b/i, score: 10, reason: "Refund lure wording detected." }
];

function getSignatureForLearning(email) {
    const subject = (email.subject || "").trim().toLowerCase();
    const bodyStart = `${email.body || ""}`.trim().toLowerCase().slice(0, 120);
    const snippetStart = `${email.snippet || ""}`.trim().toLowerCase().slice(0, 120);
    return `${subject}::${bodyStart || snippetStart}`;
}

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
    return `${CACHE_VERSION}:${analysisMode}:${emailText}`;
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

function collectLocalSignals(emailText, sender = "") {
    const matches = [];
    let score = 15;

    for (const item of LOCAL_SPAM_PATTERNS) {
        if (item.pattern.test(emailText)) {
            matches.push(item);
            score += item.score;
        }
    }

    if (TRUSTED_SENDER_PATTERNS.some((pattern) => pattern.test(sender))) {
        score -= 20;
    }

    if (/\bsecurity alert\b/i.test(emailText) && TRUSTED_SENDER_PATTERNS.some((pattern) => pattern.test(sender))) {
        score -= 10;
    }

    if (matches.length >= 2) {
        score += 10;
    }

    if (
        matches.some((item) => /lottery|winner|won|prize/i.test(item.reason)) &&
        matches.some((item) => /bank|identity|payment/i.test(item.reason))
    ) {
        score += 20;
    }

    score = Math.max(5, Math.min(score, 98));
    return { score, matches };
}

function buildKeywordList(rawKeywords, localMatches) {
    const keywords = rawKeywords.map((keyword) => {
        if (typeof keyword === "string") {
            return { word: keyword, importance: 0.5 };
        }

        return {
            word: keyword.word || "",
            importance: typeof keyword.importance === "number" ? keyword.importance : 0.5
        };
    }).filter((keyword) => keyword.word);

    localMatches.forEach((item) => {
        const word = item.reason.replace(/\.$/, "");
        if (!keywords.some((keyword) => keyword.word === word)) {
            keywords.push({
                word,
                importance: item.score / 100
            });
        }
    });

    return keywords.slice(0, 6);
}

function normalizePrediction(result, emailText, sender = "") {
    const backendRiskScore = Number(result.risk_score) || 0;
    const backendReasons = Array.isArray(result.reasons) ? result.reasons : [];
    const rawKeywords = Array.isArray(result.keywords) ? result.keywords : [];
    const localSignals = collectLocalSignals(emailText, sender);

    const riskScore = Math.max(
        backendRiskScore,
        localSignals.score >= 45 ? localSignals.score : backendRiskScore
    );

    const reasons = [...new Set([
        ...backendReasons,
        ...localSignals.matches.map((item) => item.reason)
    ])];

    const contributingKeywords = buildKeywordList(rawKeywords, localSignals.matches);

    const intentSummary = reasons.length > 0
        ? reasons.join(" ")
        : (riskScore >= 70 ? "This email shows strong spam or phishing signals." : "No major spam indicators were detected.");

    const dangerous = result.label === "Dangerous" || riskScore >= 75;
    const suspicious = riskScore >= 45 || reasons.length > 0;
    const isSpam = dangerous || suspicious;

    return {
        label: dangerous ? "Dangerous" : (isSpam ? "Suspicious" : "Safe"),
        risk_score: riskScore,
        confidence: riskScore / 100,
        reasons,
        keywords: rawKeywords,
        isSpam,
        explanation: intentSummary,
        intentSummary,
        warningMessage: reasons[0] || "",
        suggestedFilter: dangerous ? "Move to Spam / Quarantine" : (isSpam ? "Review before trusting" : "Keep in Inbox"),
        contributingKeywords,
        emailText
    };
}

function getLocalPreviewAnalysis(email) {
    const emailText = `${email.subject || ""} ${email.snippet || ""}`.trim() || "No content";
    const sender = email.sender || "";
    const localSignals = collectLocalSignals(emailText, sender);
    const isSpam = localSignals.score >= 45;

    return {
        label: isSpam ? (localSignals.score >= 75 ? "Dangerous" : "Suspicious") : "Safe",
        risk_score: localSignals.score,
        confidence: localSignals.score / 100,
        reasons: localSignals.matches.slice(0, 2).map((item) => item.reason),
        keywords: localSignals.matches.slice(0, 4).map((item) => item.reason.replace(/\.$/, "")),
        isSpam,
        explanation: localSignals.matches.length > 0 ? localSignals.matches[0].reason : "No major spam indicators were detected.",
        intentSummary: localSignals.matches.length > 0 ? localSignals.matches.map((item) => item.reason).join(" ") : "No major spam indicators were detected.",
        warningMessage: localSignals.matches[0]?.reason || "",
        suggestedFilter: isSpam ? "Review before opening" : "Keep in Inbox",
        contributingKeywords: localSignals.matches.slice(0, 4).map((item) => ({
            word: item.reason.replace(/\.$/, ""),
            importance: item.score / 100
        })),
        emailText,
        analysisSource: "local-preview",
        previewOnly: true
    };
}

async function getLearnedVerdict(email) {
    if (!globalThis.chrome?.storage?.local) {
        return null;
    }

    const signature = getSignatureForLearning(email);
    if (!signature.trim()) {
        return null;
    }

    const stored = await chrome.storage.local.get(["learnedVerdicts"]);
    const learnedVerdicts = Array.isArray(stored.learnedVerdicts) ? stored.learnedVerdicts : [];
    const exactMatch = learnedVerdicts.find((entry) => entry.signature === signature);
    if (exactMatch) {
        return exactMatch.verdict;
    }

    const [subject, textStart] = signature.split("::");
    for (const entry of learnedVerdicts) {
        const [savedSubject, savedTextStart] = `${entry.signature || ""}`.split("::");
        const subjectMatches = savedSubject && subject && savedSubject === subject;
        const textMatches = savedTextStart && textStart && (savedTextStart.includes(textStart.slice(0, 40)) || textStart.includes(savedTextStart.slice(0, 40)));
        if (subjectMatches || textMatches) {
            return entry.verdict;
        }
    }

    return null;
}

function applyLearnedVerdict(result, verdict) {
    if (!verdict) {
        return result;
    }

    if (verdict === "spam") {
        return {
            ...result,
            label: "Dangerous",
            risk_score: Math.max(result.risk_score || 0, 90),
            confidence: Math.max(result.confidence || 0, 0.9),
            isSpam: true,
            reasons: [...new Set(["User quarantined this email as spam.", ...(result.reasons || [])])],
            explanation: "User quarantined this email as spam.",
            intentSummary: "User quarantined this email as spam.",
            warningMessage: "User quarantined this email as spam.",
            suggestedFilter: "Move to Spam / Quarantine"
        };
    }

    if (verdict === "safe") {
        return {
            ...result,
            label: "Safe",
            risk_score: Math.min(result.risk_score || 100, 15),
            confidence: 0.15,
            isSpam: false,
            reasons: ["User marked this email as safe."],
            explanation: "User marked this email as safe.",
            intentSummary: "User marked this email as safe.",
            warningMessage: "",
            suggestedFilter: "Keep in Inbox"
        };
    }

    return result;
}

async function getEmailAnalysis(email) {
    const emailText = `${email.subject || ""} ${email.snippet || ""} ${email.body || ""}`.trim() || "No content";
    const analysisMode = email.analysisMode === "preview" ? "preview" : "full";
    const learnedVerdict = await getLearnedVerdict(email);

    if (analysisMode === "preview") {
        return applyLearnedVerdict(getLocalPreviewAnalysis(email), learnedVerdict);
    }

    const cached = readCachedAnalysis(emailText, analysisMode);
    if (cached) {
        return applyLearnedVerdict(cached, learnedVerdict);
    }

    const payload = {
        email_text: emailText,
        html_content: analysisMode === "full" ? (email.body || "") : "",
        analysis_mode: analysisMode
    };

    try {
        const result = await securePost("/predict", payload);
        const normalized = normalizePrediction(result, emailText, email.sender || "");
        storeCachedAnalysis(emailText, analysisMode, normalized);
        return applyLearnedVerdict(normalized, learnedVerdict);
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
