const API_BASE_URL = "http://127.0.0.1:8002";
const API_KEY = "dev-secret-key-12345";

let requestQueue = Promise.resolve();

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
        const timeoutId = setTimeout(() => controller.abort(), 10000);

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

async function getEmailAnalysis(email) {
    const emailText = `${email.subject || ""} ${email.snippet || ""} ${email.body || ""}`.trim() || "No content";
    const payload = {
        email_text: emailText,
        html_content: email.body || ""
    };

    try {
        const result = await securePost("/predict", payload);
        return normalizePrediction(result, emailText);
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
