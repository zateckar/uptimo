// ============================================================================
// UNIFIED FEEDBACK SYSTEM
// This file provides standardized feedback mechanisms for the Uptimo application
// ============================================================================

// Unified Feedback System
const FeedbackManager = {
    // Configuration
    config: {
        defaultToastDuration: 5000,
        maxToasts: 5,
        autoHideSuccess: true,
        autoHideErrors: false,
        animationDuration: 300
    },

    // Initialize the feedback system
    init: function() {
        this.createToastContainer();
        this.setupGlobalErrorHandlers();
        console.log('Feedback system initialized');
    },

    // Show form validation feedback
    showFieldError: function(fieldId, message, options = {}) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.warn(`Field with ID '${fieldId}' not found`);
            return;
        }

        const fieldGroup = field.closest('.form-group') || field.parentNode;
        const existingError = fieldGroup.querySelector('.form-error');
        const existingSuccess = fieldGroup.querySelector('.form-success');
        
        // Remove existing feedback
        if (existingError) existingError.remove();
        if (existingSuccess) existingSuccess.remove();
        
        // Add error classes
        field.classList.add('is-invalid');
        field.classList.remove('is-valid', 'is-warning');
        
        // Update form group state
        fieldGroup.classList.add('has-error');
        fieldGroup.classList.remove('has-success', 'has-warning');
        
        // Create error element
        const errorElement = document.createElement('div');
        errorElement.className = 'form-error';
        errorElement.textContent = message;
        errorElement.setAttribute('role', 'alert');
        errorElement.setAttribute('aria-live', 'polite');
        errorElement.setAttribute('data-feedback-for', fieldId);
        
        // Insert after field or its label
        const insertAfter = fieldGroup.querySelector('.form-label') || field;
        insertAfter.parentNode.insertBefore(errorElement, insertAfter.nextSibling);
        
        // Focus the field if requested
        if (options.focus !== false) {
            field.focus();
        }
        
        // Announce to screen readers
        this.announceToScreenReader(`Error in ${this.getFieldLabel(field)}: ${message}`);
    },

    // Show success feedback
    showFieldSuccess: function(fieldId, message = '', options = {}) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.warn(`Field with ID '${fieldId}' not found`);
            return;
        }

        const fieldGroup = field.closest('.form-group') || field.parentNode;
        const existingError = fieldGroup.querySelector('.form-error');
        const existingSuccess = fieldGroup.querySelector('.form-success');
        
        // Remove existing feedback
        if (existingError) existingError.remove();
        if (existingSuccess) existingSuccess.remove();
        
        // Add success classes
        field.classList.add('is-valid');
        field.classList.remove('is-invalid', 'is-warning');
        
        // Update form group state
        fieldGroup.classList.add('has-success');
        fieldGroup.classList.remove('has-error', 'has-warning');
        
        // Create success element if message provided
        if (message) {
            const successElement = document.createElement('div');
            successElement.className = 'form-success';
            successElement.textContent = message;
            successElement.setAttribute('role', 'status');
            successElement.setAttribute('aria-live', 'polite');
            successElement.setAttribute('data-feedback-for', fieldId);
            
            const insertAfter = fieldGroup.querySelector('.form-label') || field;
            insertAfter.parentNode.insertBefore(successElement, insertAfter.nextSibling);
            
            // Auto-remove after duration
            if (options.autoHide !== false) {
                setTimeout(() => {
                    if (successElement.parentNode) {
                        successElement.remove();
                    }
                }, options.duration || this.config.defaultToastDuration);
            }
        }
        
        // Announce to screen readers
        if (message) {
            this.announceToScreenReader(`${this.getFieldLabel(field)}: ${message}`);
        }
    },

    // Show warning feedback
    showFieldWarning: function(fieldId, message, options = {}) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.warn(`Field with ID '${fieldId}' not found`);
            return;
        }

        const fieldGroup = field.closest('.form-group') || field.parentNode;
        const existingFeedback = fieldGroup.querySelector('.form-error, .form-success, .form-warning');
        
        // Remove existing feedback
        if (existingFeedback) existingFeedback.remove();
        
        // Add warning classes
        field.classList.add('is-warning');
        field.classList.remove('is-valid', 'is-invalid');
        
        // Update form group state
        fieldGroup.classList.add('has-warning');
        fieldGroup.classList.remove('has-success', 'has-error');
        
        // Create warning element
        const warningElement = document.createElement('div');
        warningElement.className = 'form-warning';
        warningElement.textContent = message;
        warningElement.setAttribute('role', 'alert');
        warningElement.setAttribute('aria-live', 'polite');
        warningElement.setAttribute('data-feedback-for', fieldId);
        
        const insertAfter = fieldGroup.querySelector('.form-label') || field;
        insertAfter.parentNode.insertBefore(warningElement, insertAfter.nextSibling);
        
        // Focus the field if requested
        if (options.focus !== false) {
            field.focus();
        }
        
        // Announce to screen readers
        this.announceToScreenReader(`Warning for ${this.getFieldLabel(field)}: ${message}`);
    },

    // Clear all feedback for a form
    clearFormFeedback: function(formId) {
        const form = document.getElementById(formId);
        if (!form) return;
        
        // Remove all validation classes
        form.querySelectorAll('.is-invalid, .is-valid, .is-warning').forEach(field => {
            field.classList.remove('is-invalid', 'is-valid', 'is-warning');
        });
        
        // Remove all feedback messages
        form.querySelectorAll('.form-error, .form-success, .form-warning').forEach(msg => {
            msg.remove();
        });
        
        // Clear form group states
        form.querySelectorAll('.has-error, .has-success, .has-warning').forEach(group => {
            group.classList.remove('has-error', 'has-success', 'has-warning');
        });
    },

    // Clear feedback for a specific field
    clearFieldFeedback: function(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        
        const fieldGroup = field.closest('.form-group') || field.parentNode;
        
        // Remove validation classes
        field.classList.remove('is-invalid', 'is-valid', 'is-warning');
        
        // Remove feedback messages
        fieldGroup.querySelectorAll('.form-error, .form-success, .form-warning').forEach(msg => {
            msg.remove();
        });
        
        // Clear form group state
        fieldGroup.classList.remove('has-error', 'has-success', 'has-warning');
    },

    // Show loading state
    showLoading: function(elementId, loadingText = 'Loading...', options = {}) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Store original content if not already stored
        if (!element.dataset.originalContent) {
            element.dataset.originalContent = element.innerHTML;
        }
        
        // Add loading class
        element.classList.add('loading');
        element.disabled = true;
        
        if (element.tagName === 'BUTTON' || element.classList.contains('btn')) {
            // Button loading state
            element.innerHTML = `
                <span class="visually-hidden">${loadingText}</span>
                <span aria-hidden="true">
                    <i class="bi bi-hourglass-split me-2"></i>
                    ${loadingText}
                </span>
            `;
        } else {
            // General element loading state
            element.innerHTML = `
                <div class="d-flex align-items-center gap-2">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">${loadingText}</span>
                    </div>
                    <span>${loadingText}</span>
                </div>
            `;
        }
        
        // Announce to screen readers
        if (options.announce !== false) {
            this.announceToScreenReader(loadingText);
        }
    },

    // Restore element state
    restoreElement: function(elementId, options = {}) {
        const element = document.getElementById(elementId);
        if (!element || !element.dataset.originalContent) return;
        
        element.innerHTML = element.dataset.originalContent;
        element.disabled = false;
        element.classList.remove('loading');
        delete element.dataset.originalContent;
        
        // Announce completion if requested
        if (options.announce) {
            this.announceToScreenReader(options.announce);
        }
    },

    // Show toast notification
    showToast: function(message, type = 'info', options = {}) {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        // Check if we should exceed max toasts
        const existingToasts = toastContainer.querySelectorAll('.toast');
        if (existingToasts.length >= this.config.maxToasts) {
            existingToasts[0].remove();
        }
        
        const toastId = 'toast-' + Date.now() + Math.random().toString(36).substr(2, 9);
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.id = toastId;
        
        const iconMap = {
            'success': 'check-circle-fill',
            'danger': 'exclamation-triangle-fill',
            'warning': 'exclamation-circle-fill',
            'info': 'info-circle-fill'
        };
        
        const titleMap = {
            'success': 'Success',
            'danger': 'Error',
            'warning': 'Warning',
            'info': 'Information'
        };
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${iconMap[type]} me-2" aria-hidden="true"></i>
                    <strong class="me-2">${titleMap[type]}:</strong>
                    <span>${message}</span>
                </div>
                <button type="button" 
                        class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" 
                        aria-label="Close this notification"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: options.autoHide !== false && this.shouldAutoHide(type),
            delay: options.duration || this.config.defaultToastDuration
        });
        
        bsToast.show();
        
        // Announce to screen readers
        this.announceToScreenReader(`${titleMap[type]}: ${message}`);
        
        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
        
        return bsToast;
    },

    // Determine if toast should auto-hide based on type
    shouldAutoHide: function(type) {
        switch (type) {
            case 'success':
            case 'info':
                return this.config.autoHideSuccess;
            case 'danger':
            case 'warning':
                return this.config.autoHideErrors;
            default:
                return true;
        }
    },

    // Create toast container if it doesn't exist
    createToastContainer: function() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3 toast-container-zindex-9999';
            container.id = 'toastContainer';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-label', 'Notifications');
            document.body.appendChild(container);
        }
        return container;
    },

    // Announce message to screen readers
    announceToScreenReader: function(message, priority = 'polite') {
        const announcement = document.createElement('div');
        announcement.className = 'sr-only-validation';
        announcement.setAttribute('aria-live', priority);
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        // Remove after announcement
        setTimeout(() => {
            announcement.remove();
        }, 1000);
    },

    // Get field label for accessibility announcements
    getFieldLabel: function(field) {
        // Try to find associated label
        const label = document.querySelector(`label[for="${field.id}"]`);
        if (label) {
            return label.textContent.trim();
        }
        
        // Try to find label in form group
        const fieldGroup = field.closest('.form-group');
        if (fieldGroup) {
            const groupLabel = fieldGroup.querySelector('.form-label');
            if (groupLabel) {
                return groupLabel.textContent.trim();
            }
        }
        
        // Use placeholder or name
        return field.placeholder || field.name || 'Field';
    },

    // Setup global error handlers
    setupGlobalErrorHandlers: function() {
        // Handle form submission errors
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.tagName === 'FORM') {
                // Clear previous feedback before submission
                const formId = form.id || 'form-' + Date.now();
                if (!form.id) {
                    form.id = formId;
                }
                
                // Show loading state for submit button
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    this.showLoading(submitBtn.id || this.generateButtonId(submitBtn), 'Submitting...');
                }
            }
        });

        // Handle AJAX request failures
        window.addEventListener('unhandledrejection', (event) => {
            if (event.reason && event.reason.name !== 'AbortError') {
                this.showToast('An unexpected error occurred. Please try again.', 'danger');
                console.error('Unhandled promise rejection:', event.reason);
            }
        });
    },

    // Generate ID for button without ID
    generateButtonId: function(button) {
        return 'btn-' + button.textContent.trim().toLowerCase().replace(/\s+/g, '-') + '-' + Date.now();
    },

    // Validate form field
    validateField: function(fieldId, rules, options = {}) {
        const field = document.getElementById(fieldId);
        if (!field) return false;
        
        const value = field.value.trim();
        
        // Clear existing feedback
        this.clearFieldFeedback(fieldId);
        
        // Run validation rules
        for (const rule of rules) {
            const result = rule(value, field);
            
            if (result !== true) {
                if (typeof result === 'string') {
                    this.showFieldError(fieldId, result, options);
                } else if (result.type === 'warning') {
                    this.showFieldWarning(fieldId, result.message, options);
                }
                return false;
            }
        }
        
        // Show success if requested
        if (options.showSuccess !== false) {
            this.showFieldSuccess(fieldId, options.successMessage || '');
        }
        
        return true;
    },

    // Validate entire form
    validateForm: function(formId, fieldRules, options = {}) {
        const form = document.getElementById(formId);
        if (!form) return false;
        
        let isValid = true;
        const firstInvalidField = null;
        
        // Validate each field
        for (const [fieldId, rules] of Object.entries(fieldRules)) {
            const fieldValid = this.validateField(fieldId, rules, {
                focus: false, // Don't focus yet, focus first invalid field later
                ...options
            });
            
            if (!fieldValid && isValid) {
                isValid = false;
                firstInvalidField = document.getElementById(fieldId);
            }
        }
        
        // Focus first invalid field
        if (firstInvalidField && options.focusFirstInvalid !== false) {
            firstInvalidField.focus();
        }
        
        // Show form-level message
        if (!isValid && options.formMessage) {
            this.showToast(options.formMessage, 'danger');
        }
        
        return isValid;
    }
};

// Initialize feedback system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    FeedbackManager.init();
});

// Export for global use
window.FeedbackManager = FeedbackManager;