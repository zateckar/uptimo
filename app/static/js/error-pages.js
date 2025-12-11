/**
 * Error Pages JavaScript
 * Handles functionality for error pages like 404
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle back button functionality for multiple elements
    const goBackButtons = [
        document.getElementById('go-back-btn'),
        ...document.querySelectorAll('[data-action="go-back"]')
    ];
    
    goBackButtons.forEach(button => {
        if (button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                window.history.back();
            });
        }
    });
});