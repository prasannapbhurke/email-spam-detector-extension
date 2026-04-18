// PRODUCTION CONFIGURATION
const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

function getErrorMessage(error) {
    if (error instanceof Error && error.message) return error.message;
    return String(error);
}

async function securePost(endpoint, body) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000); // 20s for production cold starts

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
    } finally {
        clearTimeout(timeoutId);
    }
}

async function getEmailAnalysis(email) {
    // FIX: Ensure no 'undefined' strings are sent to the backend
    const payload = {
        email_text: `${email.subject || ""} ${email.snippet || ""} ${email.body || ""}`.trim() || "No content",
        html_content: email.body || ""
    };

    try {
        const result = await securePost("/predict", payload);
        return {
            label: result.label,
            risk_score: result.risk_score,
            confidence: result.confidence,
            reasons: result.reasons || [],
            keywords: result.keywords || [],
            // Mapping for UI backward compatibility
            isSpam: result.label !== "Safe",
            explanation: result.reasons.join(". "),
            contributingKeywords: result.keywords.map(kw => ({ word: kw, importance: 0.5 }))
        };
    } catch (error) {
        console.error("Spam analysis failed:", getErrorMessage(error));
        return null;
    }
}

async function sendFeedback(emailObj, isActuallySpam) {
    const feedbackPayload = {
        text: `${emailObj.subject || ""} ${emailObj.body || ""}`,
        prediction: isActuallySpam ? "spam" : "ham",
        isActuallySpam: isActuallySpam
    };
    try {
        await securePost("/feedback", feedbackPayload);
        console.log("Feedback logged successfully");
    } catch (error) {
        console.error("Feedback submission failed:", getErrorMessage(error));
    }
}
