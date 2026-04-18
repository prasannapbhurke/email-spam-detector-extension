// PRODUCTION CONFIGURATION
const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

async function securePost(endpoint, body) {
    const controller = new AbortController();
    // 30 seconds for cloud cold start + transformer loading
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
        console.log(`📡 AI Assistant: Sending request to ${endpoint}...`);
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
            console.error(`❌ API Error (${response.status}):`, text);
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log(`✅ AI Assistant: Received response from ${endpoint}`);
        return data;
    } catch (err) {
        if (err.name === "AbortError") {
            console.warn("⏳ AI Assistant: Request timed out. Cloud model is still waking up.");
        } else {
            console.error("🌐 AI Assistant: Network error.", err);
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

async function getEmailAnalysis(email) {
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
            explanation: (result.reasons || []).join(". "),
            contributingKeywords: (result.keywords || []).map(kw => ({ word: kw, importance: 0.5 }))
        };
    } catch (error) {
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
        console.error("Feedback failed");
    }
}
