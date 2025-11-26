// Notification History Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll to expanded message
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(function(button) {
        button.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-bs-target'));
            if (target && !target.classList.contains('show')) {
                setTimeout(function() {
                    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            }
        });
    });
});

// Auto-refresh functionality with user activity detection
function setupAutoRefresh() {
    let refreshTimer;
    let userIsActive = true; // Start assuming user is active
    const inactivityTime = 30000; // 30 seconds of inactivity before refresh

    // Reset timer on user activity
    function resetTimer() {
        userIsActive = true;
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(() => {
            userIsActive = false;
            window.location.reload();
        }, inactivityTime);
    }

    // Reset timer on various user interactions
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
        document.addEventListener(event, resetTimer, true);
    });

    // Start the initial timer
    resetTimer();
}

// Initialize auto-refresh if there are notifications
if (document.querySelector('.table-responsive')) {
    setupAutoRefresh();
}