// PRODUCTION CONFIGURATION
const API_BASE_URL = "https://web-production-edebc.up.railway.app";
const API_KEY = "dev-secret-key-12345";

// Request Queue to prevent flooding the server
let requestQueue = Promise.resolve();

async function securePost(endpoint, body) {
    // Chain the request to the queue (One at a time)
    return requestQueue = requestQueue.then(async () => {
        const controller = new AbortController();
        // 45 seconds for cloud cold-start (model download + load)
        const timeoutId = setTimeout(() => controller.abort(), 45000);

        try {
            console.log(`📡 AI Assistant: Processing ${endpoint}...`);
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
            console.log(`✅ AI Assistant: Done.`);
            return data;
        } catch (err) {
            if (err.name === "AbortError") {
                console.warn("⏳ AI Assistant: Server is taking too long to load AI. Cloud model is still waking up.");
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
