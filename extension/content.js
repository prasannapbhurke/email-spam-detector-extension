// Initialize the assistant
function init() {
    // Check if the observer script has loaded its main function
    if (typeof startObserving === 'function') {
        startObserving();
    } else {
        // Fallback for race conditions
        setTimeout(init, 500);
    }
}

init();
