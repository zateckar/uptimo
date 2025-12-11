// Uptimo JavaScript - Public Status Pages Management
// This file handles the public status pages list functionality

// Public Status Pages Manager
const PublicStatusPagesManager = {
    // Initialize all event listeners
    init: function() {
        this.initStatusToggles();
        this.initCopyUrlButtons();
    },

    // Initialize status toggle functionality
    initStatusToggles: function() {
        const toggleElements = document.querySelectorAll('.status-toggle');
        
        toggleElements.forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const pageId = e.target.getAttribute('data-page-id');
                const isActive = e.target.checked;
                this.toggleStatus(pageId, isActive, e.target);
            });
        });
    },


    // Initialize copy URL functionality
    initCopyUrlButtons: function() {
        const copyButtons = document.querySelectorAll('.copy-url');
        
        copyButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const url = button.getAttribute('data-url');
                navigator.clipboard.writeText(url).then(() => {
                    const originalTitle = button.getAttribute('title');
                    button.setAttribute('title', 'Copied!');
                    button.classList.add('btn-success');
                    button.classList.remove('btn-outline-secondary');
                    
                    setTimeout(() => {
                        button.setAttribute('title', originalTitle);
                        button.classList.remove('btn-success');
                        button.classList.add('btn-outline-secondary');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            });
        });
    },

    // Toggle status page active status
    toggleStatus: function(pageId, isActive, checkboxElement) {
        fetch(`/admin/public-status/${pageId}/toggle-active`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({ is_active: isActive })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                this.showSuccessMessage(`Status page ${isActive ? 'activated' : 'deactivated'} successfully.`);
                
                // Update badge
                const badgeElement = checkboxElement.closest('td').querySelector('.badge');
                if (badgeElement) {
                    badgeElement.className = `badge bg-${isActive ? 'success' : 'secondary'}`;
                    badgeElement.textContent = isActive ? 'Active' : 'Inactive';
                }
            } else {
                // Revert checkbox on error
                checkboxElement.checked = !isActive;
                alert('Error updating status: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            // Revert checkbox on error
            checkboxElement.checked = !isActive;
            console.error('Error:', error);
            alert('Error updating status');
        });
    },

    // Show success message
    showSuccessMessage: function(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container-fluid');
        const firstChild = container.firstChild;
        
        if (firstChild) {
            container.insertBefore(alertDiv, firstChild);
        } else {
            container.appendChild(alertDiv);
        }
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
};

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the public status pages list
    if (document.querySelector('.status-toggle') || document.querySelector('.copy-url')) {
        PublicStatusPagesManager.init();
    }
});

// Export for global access
window.PublicStatusPagesManager = PublicStatusPagesManager;