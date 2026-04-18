console.log("Smart Gmail Spam Detector is active.");

// Initialize the observer
function init() {
    // Gmail is a Single Page App (SPA).
    // We start observing when the document is ready.
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        startObservingInbox();
    } else {
        window.addEventListener('load', startObservingInbox);
    }
}

init();
