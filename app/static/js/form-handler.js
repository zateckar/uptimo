/**
 * Enhanced Form Handler with Validation System
 * Handles form interactions for monitor create/edit pages with comprehensive validation
 */

// Enhanced Form Handler with Validation
const FormHandler = {
    // Validation rules library
    validationRules: {
        required: function(value) {
            if (!value || value.trim() === '') {
                return 'This field is required';
            }
            return true;
        },
        
        minLength: function(minLength) {
            return function(value) {
                if (value.length < minLength) {
                    return `Must be at least ${minLength} characters long`;
                }
                return true;
            };
        },
        
        maxLength: function(maxLength) {
            return function(value) {
                if (value.length > maxLength) {
                    return `Must be no more than ${maxLength} characters long`;
                }
                return true;
            };
        },
        
        email: function(value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                return 'Please enter a valid email address';
            }
            return true;
        },
        
        url: function(value) {
            try {
                new URL(value);
                return true;
            } catch {
                return 'Please enter a valid URL (including http:// or https://)';
            }
        },
        
        number: function(value) {
            if (isNaN(Number(value))) {
                return 'Please enter a valid number';
            }
            return true;
        },
        
        positiveNumber: function(value) {
            const num = Number(value);
            if (isNaN(num) || num <= 0) {
                return 'Please enter a positive number';
            }
            return true;
        },
        
        portNumber: function(value) {
            const port = Number(value);
            if (isNaN(port) || port < 1 || port > 65535) {
                return 'Please enter a valid port number (1-65535)';
            }
            return true;
        },
        
        json: function(value) {
            try {
                JSON.parse(value);
                return true;
            } catch {
                return 'Please enter valid JSON';
            }
        }
    },

    // Store validation rules for real-time validation
    fieldValidationRules: {},
    validationTimeout: null,

    // Initialize form handlers
    init: function() {
        // Check for FeedbackManager dependency
        if (typeof FeedbackManager === 'undefined') {
            console.error('FeedbackManager not loaded. Form validation may not work.');
        }
        
        // Initialize original functionality
        this.initializeDomainAutoFill();
        this.initializeDeleteButton();
        this.initializeCloneButton();
        
        // Initialize enhanced functionality
        this.setupFormHandlers();
        this.setupRealtimeValidation();
        
        console.log('Enhanced form handler initialized');
    },

    // Initialize domain auto-fill functionality based on monitor type
    initializeDomainAutoFill: function() {
        const targetField = document.getElementById('target');
        const checkDomainCheckbox = document.getElementById('check_domain');
        const expectedDomainField = document.getElementById('expected_domain');
        
        if (!targetField || !checkDomainCheckbox || !expectedDomainField) {
            return;
        }
        
        // Determine monitor type from the hidden type field
        const typeField = document.querySelector('input[name="type"]');
        const monitorType = typeField ? typeField.value : 'http';
        
        // Auto-fill expected domain based on target field
        targetField.addEventListener('blur', () => {
            if (!checkDomainCheckbox.checked || expectedDomainField.value || !targetField.value) {
                return;
            }
            
            const domain = this.extractDomain(targetField.value, monitorType);
            if (domain) {
                expectedDomainField.value = domain;
            }
        });
        
        // Handle domain checkbox toggle
        checkDomainCheckbox.addEventListener('change', () => {
            expectedDomainField.disabled = !checkDomainCheckbox.checked;
            
            if (checkDomainCheckbox.checked && !expectedDomainField.value && targetField.value) {
                const domain = this.extractDomain(targetField.value, monitorType);
                if (domain) {
                    expectedDomainField.value = domain;
                }
            }
        });
        
        // Initialize expected domain field state
        expectedDomainField.disabled = !checkDomainCheckbox.checked;
    },

    // Extract domain from target value based on monitor type
    extractDomain: function(targetValue, monitorType) {
        try {
            switch (monitorType) {
                case 'http':
                    // Extract hostname from URL
                    const url = new URL(targetValue);
                    return url.hostname;
                    
                case 'kafka':
                    // Extract hostname from broker address (host:port)
                    const parts = targetValue.split(':');
                    return parts.length > 0 ? parts[0] : '';
                    
                case 'tcp':
                case 'ping':
                    // Use target value directly (hostname or IP)
                    return targetValue;
                    
                default:
                    return '';
            }
        } catch (e) {
            // Invalid format, return empty string
            return '';
        }
    },

    // Initialize delete button functionality for edit mode
    initializeDeleteButton: function() {
        const deleteBtn = document.getElementById('deleteMonitorBtn');
        const deleteForm = document.getElementById('deleteForm');
        
        if (!deleteBtn || !deleteForm) {
            return;
        }
        
        deleteBtn.addEventListener('click', function(event) {
            event.preventDefault();
            
            if (confirm('Are you sure you want to delete this monitor?')) {
                deleteForm.submit();
            }
        });
    },

    // Initialize clone button functionality for edit mode
    initializeCloneButton: function() {
        const cloneBtn = document.getElementById('cloneMonitorBtn');
        const cloneForm = document.getElementById('cloneForm');
        
        if (!cloneBtn || !cloneForm) {
            return;
        }
        
        cloneBtn.addEventListener('click', function(event) {
            event.preventDefault();
            
            if (confirm('Clone this monitor? A copy will be created as inactive.')) {
                cloneForm.submit();
            }
        });
    },

    // Setup form submission handlers
    setupFormHandlers: function() {
        // Handle HTTP monitor form
        const httpForm = document.querySelector('form[action*="create_http"], form[action*="edit"]');
        if (httpForm) {
            this.setupHttpMonitorForm(httpForm);
        }

        // Handle TCP monitor form
        const tcpForm = document.querySelector('form[action*="create_tcp"]');
        if (tcpForm) {
            this.setupTcpMonitorForm(tcpForm);
        }

        // Handle Ping monitor form
        const pingForm = document.querySelector('form[action*="create_ping"]');
        if (pingForm) {
            this.setupPingMonitorForm(pingForm);
        }

        // Handle Kafka monitor form
        const kafkaForm = document.querySelector('form[action*="create_kafka"]');
        if (kafkaForm) {
            this.setupKafkaMonitorForm(kafkaForm);
        }
    },

    // Setup HTTP monitor form validation
    setupHttpMonitorForm: function(form) {
        const formId = form.id || 'http-monitor-form';
        if (!form.id) form.id = formId;

        // Validation rules for HTTP monitor form
        const fieldRules = {
            name: [
                this.validationRules.required,
                this.validationRules.minLength(2),
                this.validationRules.maxLength(100)
            ],
            target: [
                this.validationRules.required,
                this.validationRules.url
            ],
            timeout: [
                this.validationRules.required,
                this.validationRules.positiveNumber,
                this.validationRules.maxLength(10)
            ],
            check_interval: [
                this.validationRules.required,
                this.validationRules.positiveNumber
            ],
            response_time_threshold: [
                this.validationRules.number,
                this.validationRules.maxLength(10)
            ],
            expected_status_codes: [
                this.validationRules.required
            ],
            http_headers: [
                function(value) {
                    if (!value || value.trim() === '') return true;
                    return FormHandler.validationRules.json(value);
                }
            ],
            http_body: [
                function(value) {
                    if (!value || value.trim() === '') return true;
                    return FormHandler.validationRules.json(value);
                }
            ],
            json_path_match: [
                function(value) {
                    if (!value || value.trim() === '') return true;
                    // Basic JSON path validation
                    if (!value.startsWith('{') || !value.endsWith('}')) {
                        return 'JSON path must be in {"key": "value"} format';
                    }
                    return FormHandler.validationRules.json(value);
                }
            ],
            cert_expiration_threshold: [
                this.validationRules.number,
                this.validationRules.maxLength(10)
            ]
        };

        // Override form submission
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleFormSubmit(formId, fieldRules, {
                formMessage: 'Please correct the errors below before submitting.',
                successMessage: 'Monitor saved successfully!',
                submitAction: () => form.submit()
            });
        });

        // Add validation type indicators
        this.addValidationIndicators(form, fieldRules);
    },

    // Setup TCP monitor form validation
    setupTcpMonitorForm: function(form) {
        const formId = form.id || 'tcp-monitor-form';
        if (!form.id) form.id = formId;

        const fieldRules = {
            name: [
                this.validationRules.required,
                this.validationRules.minLength(2),
                this.validationRules.maxLength(100)
            ],
            target: [
                this.validationRules.required
            ],
            port: [
                this.validationRules.required,
                this.validationRules.portNumber
            ],
            timeout: [
                this.validationRules.required,
                this.validationRules.positiveNumber,
                this.validationRules.maxLength(10)
            ],
            check_interval: [
                this.validationRules.required,
                this.validationRules.positiveNumber
            ]
        };

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleFormSubmit(formId, fieldRules, {
                formMessage: 'Please correct the errors below before submitting.',
                successMessage: 'TCP monitor saved successfully!',
                submitAction: () => form.submit()
            });
        });

        this.addValidationIndicators(form, fieldRules);
    },

    // Setup Ping monitor form validation
    setupPingMonitorForm: function(form) {
        const formId = form.id || 'ping-monitor-form';
        if (!form.id) form.id = formId;

        const fieldRules = {
            name: [
                this.validationRules.required,
                this.validationRules.minLength(2),
                this.validationRules.maxLength(100)
            ],
            target: [
                this.validationRules.required
            ],
            timeout: [
                this.validationRules.required,
                this.validationRules.positiveNumber,
                this.validationRules.maxLength(10)
            ],
            check_interval: [
                this.validationRules.required,
                this.validationRules.positiveNumber
            ]
        };

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleFormSubmit(formId, fieldRules, {
                formMessage: 'Please correct the errors below before submitting.',
                successMessage: 'Ping monitor saved successfully!',
                submitAction: () => form.submit()
            });
        });

        this.addValidationIndicators(form, fieldRules);
    },

    // Setup Kafka monitor form validation
    setupKafkaMonitorForm: function(form) {
        const formId = form.id || 'kafka-monitor-form';
        if (!form.id) form.id = formId;

        const fieldRules = {
            name: [
                this.validationRules.required,
                this.validationRules.minLength(2),
                this.validationRules.maxLength(100)
            ],
            target: [
                this.validationRules.required
            ],
            timeout: [
                this.validationRules.required,
                this.validationRules.positiveNumber,
                this.validationRules.maxLength(10)
            ],
            check_interval: [
                this.validationRules.required,
                this.validationRules.positiveNumber
            ]
        };

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleFormSubmit(formId, fieldRules, {
                formMessage: 'Please correct the errors below before submitting.',
                successMessage: 'Kafka monitor saved successfully!',
                submitAction: () => form.submit()
            });
        });

        this.addValidationIndicators(form, fieldRules);
    },

    // Handle form submission with validation
    handleFormSubmit: function(formId, fieldRules, options = {}) {
        // Check if FeedbackManager is available
        if (typeof FeedbackManager === 'undefined') {
            console.warn('FeedbackManager not available, submitting form without validation');
            if (options.submitAction) {
                options.submitAction();
            }
            return;
        }

        // Clear any existing feedback
        FeedbackManager.clearFormFeedback(formId);
        
        // Show loading state on submit button
        const form = document.getElementById(formId);
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const btnId = submitBtn.id || 'submit-btn-' + Date.now();
            if (!submitBtn.id) submitBtn.id = btnId;
            FeedbackManager.showLoading(btnId, options.loadingText || 'Saving...');
        }

        // Validate form
        const isValid = FeedbackManager.validateForm(formId, fieldRules, {
            formMessage: options.formMessage || 'Please correct the errors below.',
            focusFirstInvalid: true
        });

        if (isValid) {
            // Show success message
            if (options.successMessage) {
                FeedbackManager.showToast(options.successMessage, 'success');
            }
            
            // Execute submit action
            if (options.submitAction) {
                setTimeout(() => {
                    options.submitAction();
                }, 500); // Small delay to show success message
            }
        } else {
            // Restore submit button if validation fails
            if (submitBtn) {
                FeedbackManager.restoreElement(submitBtn.id || 'submit-btn-' + Date.now());
            }
        }
    },

    // Setup real-time validation on input
    setupRealtimeValidation: function() {
        // Only setup if FeedbackManager is available
        if (typeof FeedbackManager === 'undefined') {
            return;
        }

        // Add input event listeners for real-time validation
        document.addEventListener('input', (event) => {
            // Check if event.target exists and has the required classes
            if (event.target &&
                (event.target.classList.contains('form-control') ||
                 event.target.classList.contains('form-select'))) {
                const fieldId = event.target.id;
                if (fieldId && this.fieldValidationRules && this.fieldValidationRules[fieldId]) {
                    // Debounce validation
                    clearTimeout(this.validationTimeout);
                    this.validationTimeout = setTimeout(() => {
                        this.validateFieldRealtime(fieldId);
                    }, 300);
                }
            }
        });

        // Add blur event listeners for field validation
        document.addEventListener('blur', (event) => {
            // Check if event.target exists and has the required classes
            if (event.target &&
                (event.target.classList.contains('form-control') ||
                 event.target.classList.contains('form-select'))) {
                const fieldId = event.target.id;
                if (fieldId && this.fieldValidationRules && this.fieldValidationRules[fieldId]) {
                    this.validateFieldRealtime(fieldId);
                }
            }
        }, true);
    },

    // Validate field in real-time
    validateFieldRealtime: function(fieldId) {
        // Only validate if FeedbackManager is available
        if (typeof FeedbackManager === 'undefined') {
            return;
        }

        if (!this.fieldValidationRules || !this.fieldValidationRules[fieldId]) {
            return;
        }

        const field = document.getElementById(fieldId);
        if (!field || field.value.trim() === '') {
            // Don't validate empty fields on real-time (only on submit)
            FeedbackManager.clearFieldFeedback(fieldId);
            return;
        }

        FeedbackManager.validateField(fieldId, this.fieldValidationRules[fieldId], {
            focus: false, // Don't focus on real-time validation
            showSuccess: true, // Show success feedback
            successMessage: '' // No message for success in real-time
        });
    },

    // Add visual indicators for validation requirements
    addValidationIndicators: function(form, fieldRules) {
        // Only add indicators if FeedbackManager is available
        if (typeof FeedbackManager === 'undefined') {
            return;
        }

        // Store validation rules for real-time validation
        Object.assign(this.fieldValidationRules, fieldRules);

        // Add validation hints to fields
        Object.entries(fieldRules).forEach(([fieldId, rules]) => {
            const field = document.getElementById(fieldId);
            if (!field) return;

            const fieldGroup = field.closest('.form-group') || field.parentNode;
            
            // Add validation hint if field doesn't already have helper text
            const existingHelp = fieldGroup.querySelector('.form-text, .invalid-feedback');
            if (!existingHelp && rules.length > 0) {
                const hasRequired = rules.some(rule => 
                    rule === this.validationRules.required || 
                    rule.toString().includes('required')
                );
                
                if (hasRequired) {
                    field.setAttribute('aria-required', 'true');
                    
                    // Add required indicator
                    const label = fieldGroup.querySelector('.form-label');
                    if (label && !label.querySelector('.required-indicator')) {
                        const indicator = document.createElement('span');
                        indicator.className = 'required-indicator text-danger ms-1';
                        indicator.setAttribute('aria-hidden', 'true');
                        indicator.textContent = '*';
                        label.appendChild(indicator);
                    }
                }
            }
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    FormHandler.init();
});

// Export for global use
window.FormHandler = FormHandler;