// Form validation for notification settings
document.addEventListener('DOMContentLoaded', function() {
    const notificationForm = document.getElementById('notificationForm');
    const escalateAfterMinutes = document.getElementById('escalate_after_minutes');
    
    if (notificationForm) {
        notificationForm.addEventListener('submit', function(e) {
            const channels = document.querySelectorAll('input[name="channel_ids"]:checked');
            
            if (channels.length === 0) {
                e.preventDefault();
                
                // Create alert if not exists
                let alertDiv = document.querySelector('.alert-danger');
                if (!alertDiv) {
                    alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                    alertDiv.innerHTML = `
                        Please select at least one notification channel.
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.querySelector('.card-body').prepend(alertDiv);
                }
                
                // Scroll to top
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }
    
    if (escalateAfterMinutes) {
        escalateAfterMinutes.addEventListener('input', function(e) {
            const value = parseInt(e.target.value);
            if (value && (value < 1 || value > 1440)) {
                e.target.setCustomValidity('Escalation time must be between 1 and 1440 minutes');
            } else {
                e.target.setCustomValidity('');
            }
        });
    }
});