// Uptimo JavaScript - Public Status Page Management
// This file handles the public status page creation and editing functionality

// Public Status Page Manager
const PublicStatusPageManager = {
    // Initialize monitor selection preview functionality
    initMonitorPreview: function() {
        const headerInput = document.getElementById('custom_header');
        const descriptionInput = document.getElementById('description');
        const previewHeader = document.getElementById('preview-header');
        const previewDescription = document.getElementById('preview-description');
        
        // Header preview update
        if (headerInput && previewHeader) {
            headerInput.addEventListener('input', function(e) {
                previewHeader.textContent = e.target.value || 'System Status';
            });
        }
        
        // Description preview update
        if (descriptionInput && previewDescription) {
            descriptionInput.addEventListener('input', function(e) {
                previewDescription.textContent = e.target.value || 'Check the status of our services and systems.';
            });
        }
        
        // Monitor selection preview
        this.initMonitorSelectionPreview();
        
        // Copy URL functionality
        this.initCopyUrl();
        
        // Status preview toggle
        this.initStatusPreview();
    },
    
    // Initialize monitor selection preview
    initMonitorSelectionPreview: function() {
        const monitors = document.querySelectorAll('input[name="selected_monitors"]');
        
        monitors.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateMonitorPreview();
            });
        });
        
        // Initialize preview on page load
        this.updateMonitorPreview();
    },
    
    // Update monitor preview display for create page
    updateMonitorPreviewCreate: function() {
        const selectedMonitors = document.querySelectorAll('input[name="selected_monitors"]:checked');
        
        // Hide all monitor preview items first
        document.querySelectorAll('[id^="preview-monitor-"]').forEach(element => {
            element.classList.add('d-none');
        });
        
        // Show only selected monitors
        if (selectedMonitors.length === 0) {
            // If no monitors selected, you could show a message or keep hidden
            console.log('No monitors selected');
        } else {
            selectedMonitors.forEach(checkbox => {
                const monitorId = checkbox.value;
                const previewElement = document.getElementById(`preview-monitor-${monitorId}`);
                if (previewElement) {
                    previewElement.classList.remove('d-none');
                    previewElement.classList.add('d-flex');
                }
            });
        }
    },

    // Update monitor preview display for edit page
    updateMonitorPreviewEdit: function() {
        const previewMonitors = document.getElementById('preview-monitors');
        if (!previewMonitors) return;
        
        const selectedMonitors = document.querySelectorAll('input[name="selected_monitors"]:checked');
        
        if (selectedMonitors.length === 0) {
            previewMonitors.innerHTML = '<span class="text-muted">No monitors selected</span>';
        } else {
            let html = '';
            selectedMonitors.forEach(checkbox => {
                const label = checkbox.nextElementSibling.textContent;
                html += `
                    <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                        <span>${label}</span>
                        <span class="badge bg-success">Up</span>
                    </div>
                `;
            });
            previewMonitors.innerHTML = html;
        }
    },

    // Update monitor preview display (auto-detect page type)
    updateMonitorPreview: function() {
        // Check if we're on create page (has elements with id starting with "preview-monitor-")
        if (document.querySelector('[id^="preview-monitor-"]')) {
            this.updateMonitorPreviewCreate();
        } else {
            this.updateMonitorPreviewEdit();
        }
    },
    
    // Initialize copy URL functionality
    initCopyUrl: function() {
        const copyButtons = document.querySelectorAll('.copy-url');
        
        copyButtons.forEach(button => {
            button.addEventListener('click', () => {
                const url = button.getAttribute('data-url');
                navigator.clipboard.writeText(url).then(() => {
                    const originalHTML = button.innerHTML;
                    button.innerHTML = '<i class="bi bi-check"></i> Copied!';
                    button.classList.add('btn-success');
                    button.classList.remove('btn-outline-secondary');
                    
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.classList.remove('btn-success');
                        button.classList.add('btn-outline-secondary');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            });
        });
    },
    
    // Initialize status preview toggle
    initStatusPreview: function() {
        const statusToggle = document.getElementById('is_active_preview');
        const statusText = document.getElementById('status-text');
        
        if (statusToggle && statusText) {
            statusToggle.addEventListener('change', function(e) {
                statusText.textContent = e.target.checked ? 'Active' : 'Inactive';
            });
        }
    }
};

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on a public status page form
    if (document.querySelector('.status-preview') || document.getElementById('preview-monitors')) {
        PublicStatusPageManager.initMonitorPreview();
    }
});

// Export for global access
window.PublicStatusPageManager = PublicStatusPageManager;