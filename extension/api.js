// PRODUCTION CONFIGURATION
const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

// Request Queue to prevent flooding the server
let requestQueue = Promise.resolve();

async function securePost(endpoint, body) {
    // Chain the request to the queue (One at a time)
    return requestQueue = requestQueue.then(async () => {
        const controller = new AbortController();
        // Increased to 120 seconds for deep learning cold-starts in the cloud
        // Railway free tier can be slow when downloading/loading DistilBERT
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            console.log(`📡 AI Assistant: Calling ${endpoint}...`);
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
                console.error(`❌ Backend Error (${response.status}):`, text);
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log(`✅ AI Assistant: Prediction Successful.`);
            return data;
        } catch (err) {
            if (err.name === "AbortError") {
                console.warn("⏳ AI Assistant: Cloud AI is still initializing. This happens after long periods of inactivity. Please wait 1-2 minutes.");
            } else {
                console.error("🌐 AI Assistant: Network error.", err);
            }
            throw err;
        } finally {
            clearTimeout(timeoutId);
            // Wait 500ms between requests to be polite to Railway's CPU
            await new Promise(r => setTimeout(r, 500));
        }
    });
}

async function getEmailAnalysis(email) {
    const payload = {
        email_text: `${email.subject || ""} ${email.snippet || ""} ${email.body || ""}`.trim() || "No content",
        html_content: email.body || ""
    };

    try {
        const result = await securePost("/predict", payload);
        if (!result) return null;

        return {
            label: result.label || "Analyzed",
            risk_score: result.risk_score || 0,
            confidence: result.confidence || 0.5,
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
