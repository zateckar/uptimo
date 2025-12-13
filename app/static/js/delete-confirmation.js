// Delete confirmation handlers for notification channels
document.addEventListener('DOMContentLoaded', function() {
    // Add submit event listeners to delete forms
    const deleteForms = document.querySelectorAll('.delete-channel-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!confirm('Are you sure you want to delete this channel? This action cannot be undone.')) {
                event.preventDefault();
                return false;
            }
        });
    });

    // Also handle any form with data-confirm attribute
    const confirmForms = document.querySelectorAll('form[data-confirm]');
    confirmForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const message = form.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
                return false;
            }
        });
    });
});