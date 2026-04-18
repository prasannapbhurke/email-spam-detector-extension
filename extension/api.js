// PRODUCTION CONFIGURATION
const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

function getErrorMessage(error) {
    if (error instanceof Error && error.message) return error.message;
    return String(error);
}

async function securePost(endpoint, body) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

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
    const payload = {
        id: email.id || String(Date.now()),
        subject: email.subject || "",
        sender: email.sender || "",
        snippet: email.snippet || "",
        body: email.body || "" // Full HTML body for phishing link mismatch detection
    };

    try {
        const result = await securePost("/predict", payload);
        return {
            id: result.id,
            isSpam: Boolean(result.isSpam),
            confidence: Number(result.confidence) || 0,
            explanation: result.explanation || "",
            technicalExplanation: result.technicalExplanation || "",
            contributingKeywords: Array.isArray(result.contributingKeywords) ? result.contributingKeywords : [],
            phishingAnalysis: result.phishingAnalysis // New field
        };
    } catch (error) {
        console.error("Spam analysis failed:", getErrorMessage(error));
        return null;
    }
}

async function sendFeedback(emailObj, isActuallySpam) {
    const feedbackPayload = {
        id: emailObj.id,
        text: `${emailObj.subject} ${emailObj.body}`,
        isActuallySpam: isActuallySpam
    };
    try {
        await securePost("/feedback", feedbackPayload);
    } catch (error) {
        console.error("Feedback submission failed:", getErrorMessage(error));
    }
}
