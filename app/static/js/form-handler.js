/**
 * Monitor Form Handler
 * Handles form interactions for monitor create/edit pages
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeDomainAutoFill();
    initializeDeleteButton();
    initializeCloneButton();
});

/**
 * Initialize domain auto-fill functionality based on monitor type
 */
function initializeDomainAutoFill() {
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
    targetField.addEventListener('blur', function() {
        if (!checkDomainCheckbox.checked || expectedDomainField.value || !this.value) {
            return;
        }
        
        const domain = extractDomain(this.value, monitorType);
        if (domain) {
            expectedDomainField.value = domain;
        }
    });
    
    // Handle domain checkbox toggle
    checkDomainCheckbox.addEventListener('change', function() {
        expectedDomainField.disabled = !this.checked;
        
        if (this.checked && !expectedDomainField.value && targetField.value) {
            const domain = extractDomain(targetField.value, monitorType);
            if (domain) {
                expectedDomainField.value = domain;
            }
        }
    });
    
    // Initialize expected domain field state
    expectedDomainField.disabled = !checkDomainCheckbox.checked;
}

/**
 * Extract domain from target value based on monitor type
 */
function extractDomain(targetValue, monitorType) {
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
}

/**
 * Initialize delete button functionality for edit mode
 */
function initializeDeleteButton() {
    const deleteBtn = document.getElementById('deleteMonitorBtn');
    const deleteForm = document.getElementById('deleteForm');
    
    if (!deleteBtn || !deleteForm) {
        return;
    }
    
    deleteBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to delete this monitor?')) {
            deleteForm.submit();
        }
    });
}

/**
 * Initialize clone button functionality for edit mode
 */
function initializeCloneButton() {
    const cloneBtn = document.getElementById('cloneMonitorBtn');
    const cloneForm = document.getElementById('cloneForm');
    
    if (!cloneBtn || !cloneForm) {
        return;
    }
    
    cloneBtn.addEventListener('click', function() {
        if (confirm('Clone this monitor? A copy will be created as inactive.')) {
            cloneForm.submit();
        }
    });
}