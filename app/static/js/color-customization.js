document.addEventListener('DOMContentLoaded', function() {
    // Color management system
    class ColorManager {
        constructor() {
            this.colorInputs = document.querySelectorAll('.color-input');
            this.colorTexts = document.querySelectorAll('.hex-input');
            
            this.initializeEventListeners();
            this.syncColorPickersWithFormFields();
            this.updatePreviews();
        }

        initializeEventListeners() {
            // Handle color picker changes - use both input and change events
            this.colorInputs.forEach(input => {
                input.addEventListener('input', (e) => this.handleColorInputChange(e));
                input.addEventListener('change', (e) => this.handleColorInputChange(e));
            });

            // Handle hex input changes
            this.colorTexts.forEach(input => {
                input.addEventListener('input', (e) => this.handleHexInputChange(e));
                input.addEventListener('blur', (e) => this.validateHexInput(e));
            });
        }

        syncColorPickersWithFormFields() {
            // Ensure color pickers are synchronized with the actual form field values
            this.colorInputs.forEach(colorInput => {
                const inputGroup = colorInput.closest('.input-group');
                if (inputGroup) {
                    const textInput = inputGroup.querySelector('.hex-input');
                    if (textInput) {
                        // Get the current value from the form field
                        let value = textInput.value;
                        
                        // Handle rgba values for subtle colors
                        if (value && value.startsWith('rgba')) {
                            // Convert rgba to hex by taking the first 6 characters after removing 'rgba('
                            const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                            if (match) {
                                const r = parseInt(match[1]).toString(16).padStart(2, '0');
                                const g = parseInt(match[2]).toString(16).padStart(2, '0');
                                const b = parseInt(match[3]).toString(16).padStart(2, '0');
                                value = '#' + r + g + b;
                            }
                        }
                        
                        // Fallback to placeholder or default
                        if (!value) {
                            value = textInput.getAttribute('placeholder') || '#000000';
                        }
                        
                        // Ensure it's a valid hex color before setting
                        if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                            colorInput.value = value;
                            // Also ensure text input has the same value
                            textInput.value = value.toUpperCase();
                        }
                    }
                }
            });
        }

        handleColorInputChange(event) {
            const input = event.target;
            const colorValue = input.value;
            let textInput = null;
            let inputGroup = input.closest('.input-group');

            // Strategy 1: Name-based lookup (most robust)
            if (input.id && input.id.startsWith('color-picker-')) {
                const fieldName = input.id.replace('color-picker-', '');
                textInput = document.querySelector(`input[name="${fieldName}"]`);
                
                if (!textInput) {
                    // Try alternative selector
                    textInput = document.querySelector(`[name="${fieldName}"]`);
                }
            }

            // Strategy 2: DOM traversal fallback
            if (!textInput && inputGroup) {
                textInput = inputGroup.querySelector('.hex-input');
            }

            // Strategy 3: Last resort - find any hex input in the same container
            if (!textInput && inputGroup) {
                const allHexInputs = inputGroup.querySelectorAll('input[type="text"]');
                if (allHexInputs.length > 0) {
                    textInput = allHexInputs[allHexInputs.length - 1]; // Usually the last one
                }
            }

            if (textInput) {
                // Ensure we have the input group for feedback
                if (!inputGroup) {
                    inputGroup = textInput.closest('.input-group');
                }
                
                // Force update the value with the selected color
                textInput.value = colorValue.toUpperCase();
                
                // Trigger events to notify listeners
                textInput.dispatchEvent(new Event('input', { bubbles: true }));
                textInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Trigger blur event to validate the hex input
                setTimeout(() => {
                    textInput.dispatchEvent(new Event('blur', { bubbles: true }));
                }, 10);
            }
            
            if (inputGroup) {
                this.addChangeFeedback(inputGroup);
            }
            this.updatePreviews();
        }

        handleHexInputChange(event) {
            const input = event.target;
            let hexValue = input.value.trim();
            
            // Auto-format: add # if missing and convert to uppercase
            if (hexValue && !hexValue.startsWith('#')) {
                hexValue = '#' + hexValue;
            }
            
            // Validate hex format (3, 6, or 8 characters after #)
            if (hexValue && /^#[0-9A-Fa-f]{3}$/.test(hexValue)) {
                // Convert 3-digit hex to 6-digit
                const r = hexValue[1];
                const g = hexValue[2];
                const b = hexValue[3];
                hexValue = '#' + r + r + g + g + b + b;
                input.value = hexValue.toUpperCase();
            } else if (hexValue && /^#[0-9A-Fa-f]{6}$/.test(hexValue)) {
                input.value = hexValue.toUpperCase();
            }
            
            // Update color picker if we have a valid 6-digit hex
            if (/^#[0-9A-Fa-f]{6}$/.test(hexValue)) {
                const inputGroup = input.closest('.input-group');
                const colorInput = inputGroup.querySelector('.color-input');
                
                if (colorInput) {
                    colorInput.value = hexValue;
                }
                
                this.updatePreviews();
            }
        }

        validateHexInput(event) {
            const input = event.target;
            const hexValue = input.value.trim();
            const inputGroup = input.closest('.input-group');
            
            if (hexValue === '') {
                inputGroup.classList.remove('color-error', 'color-success');
                return;
            }
            
            if (/^#[0-9A-Fa-f]{6}$/.test(hexValue)) {
                inputGroup.classList.remove('color-error');
                inputGroup.classList.add('color-success');
                setTimeout(() => inputGroup.classList.remove('color-success'), 1500);
            } else {
                inputGroup.classList.remove('color-success');
                inputGroup.classList.add('color-error');
                setTimeout(() => inputGroup.classList.remove('color-error'), 2000);
            }
        }

        addChangeFeedback(inputGroup) {
            inputGroup.classList.add('color-changed');
            setTimeout(() => inputGroup.classList.remove('color-changed'), 300);
        }

        updatePreviews() {
            // Helper function to get color value with fallback to placeholder
            const getColorValue = (fieldName, defaultValue) => {
                const input = document.querySelector(`input[name="${fieldName}"]`);
                if (!input) return defaultValue;
                return input.value || input.getAttribute('placeholder') || defaultValue;
            };

            // Update light preview - use actual values or database placeholders
            const primaryColor = getColorValue('primary_color', '#59bc87');
            const successColor = getColorValue('success_color', '#22c55e');
            const dangerColor = getColorValue('danger_color', '#dc2626');
            const warningColor = getColorValue('warning_color', '#f59e0b');
            const infoColor = getColorValue('info_color', '#06b6d4');
            const successBgColor = getColorValue('success_bg_color', '#f0fdf4');
            const dangerBgColor = getColorValue('danger_bg_color', '#fef2f2');
            const warningBgColor = getColorValue('warning_bg_color', '#fffbeb');
            const infoBgColor = getColorValue('info_bg_color', '#ecfeff');

            // Update dark preview - use actual values or database placeholders
            const darkPrimaryColor = getColorValue('dark_primary_color', '#3b82f6');
            const darkSuccessColor = getColorValue('dark_success_color', '#4ade80');
            const darkDangerColor = getColorValue('dark_danger_color', '#f87171');
            const darkWarningColor = getColorValue('dark_warning_color', '#fbbf24');
            const darkInfoColor = getColorValue('dark_info_color', '#38bdf8');
            const darkSuccessBgColor = getColorValue('dark_success_bg_color', '#052e16');
            const darkDangerBgColor = getColorValue('dark_danger_bg_color', '#1f0713');
            const darkWarningBgColor = getColorValue('dark_warning_bg_color', '#1c1305');
            const darkInfoBgColor = getColorValue('dark_info_bg_color', '#071926');

            // Apply colors to light preview
            const lightPreview = document.querySelector('.light-preview');
            if (lightPreview) {
                // Update badges
                const successBadge = lightPreview.querySelector('.preview-badge.bg-success');
                const dangerBadge = lightPreview.querySelector('.preview-badge.bg-danger');
                const warningBadge = lightPreview.querySelector('.preview-badge.bg-warning');
                const infoBadge = lightPreview.querySelector('.preview-badge.bg-info');
                
                if (successBadge) {
                    successBadge.style.backgroundColor = successBgColor;
                    successBadge.style.color = successColor;
                    successBadge.style.borderColor = successColor;
                }
                if (dangerBadge) {
                    dangerBadge.style.backgroundColor = dangerBgColor;
                    dangerBadge.style.color = dangerColor;
                    dangerBadge.style.borderColor = dangerColor;
                }
                if (warningBadge) {
                    warningBadge.style.backgroundColor = warningBgColor;
                    warningBadge.style.color = warningColor;
                    warningBadge.style.borderColor = warningColor;
                }
                if (infoBadge) {
                    infoBadge.style.backgroundColor = infoBgColor;
                    infoBadge.style.color = infoColor;
                    infoBadge.style.borderColor = infoColor;
                }
                
                // Update buttons
                const lightBtn = lightPreview.querySelector('.preview-btn.btn-primary');
                if (lightBtn) {
                    lightBtn.style.backgroundColor = primaryColor;
                    lightBtn.style.borderColor = primaryColor;
                }
            }

            // Apply colors to dark preview
            const darkPreview = document.querySelector('.dark-preview');
            if (darkPreview) {
                // Update badges
                const darkSuccessBadge = darkPreview.querySelector('.preview-badge.bg-success');
                const darkDangerBadge = darkPreview.querySelector('.preview-badge.bg-danger');
                const darkWarningBadge = darkPreview.querySelector('.preview-badge.bg-warning');
                const darkInfoBadge = darkPreview.querySelector('.preview-badge.bg-info');
                
                if (darkSuccessBadge) {
                    darkSuccessBadge.style.backgroundColor = darkSuccessBgColor;
                    darkSuccessBadge.style.color = darkSuccessColor;
                    darkSuccessBadge.style.borderColor = darkSuccessColor;
                }
                if (darkDangerBadge) {
                    darkDangerBadge.style.backgroundColor = darkDangerBgColor;
                    darkDangerBadge.style.color = darkDangerColor;
                    darkDangerBadge.style.borderColor = darkDangerColor;
                }
                if (darkWarningBadge) {
                    darkWarningBadge.style.backgroundColor = darkWarningBgColor;
                    darkWarningBadge.style.color = darkWarningColor;
                    darkWarningBadge.style.borderColor = darkWarningColor;
                }
                if (darkInfoBadge) {
                    darkInfoBadge.style.backgroundColor = darkInfoBgColor;
                    darkInfoBadge.style.color = darkInfoColor;
                    darkInfoBadge.style.borderColor = darkInfoColor;
                }
                
                // Update buttons
                const darkBtn = darkPreview.querySelector('.preview-btn.btn-primary');
                if (darkBtn) {
                    darkBtn.style.backgroundColor = darkPrimaryColor;
                    darkBtn.style.borderColor = darkPrimaryColor;
                }
            }
        }

        resetToDefaults() {
            const defaultColors = {
                // Light mode colors
                'primary_color': '#59bc87',
                'primary_hover_color': '#45a676',
                'primary_subtle_color': 'rgba(168, 255, 204, 0.15)',
                'success_color': '#22c55e',
                'success_bg_color': '#f0fdf4',
                'danger_color': '#dc2626',
                'danger_bg_color': '#fef2f2',
                'warning_color': '#f59e0b',
                'warning_bg_color': '#fffbeb',
                'info_color': '#06b6d4',
                'info_bg_color': '#ecfeff',
                'unknown_color': '#6b7280',
                'unknown_bg_color': '#f3f4f6',
                // Dark mode colors
                'dark_primary_color': '#3b82f6',
                'dark_primary_hover_color': '#60a5fa',
                'dark_primary_subtle_color': 'rgba(59, 130, 246, 0.15)',
                'dark_success_color': '#4ade80',
                'dark_success_bg_color': '#052e16',
                'dark_danger_color': '#f87171',
                'dark_danger_bg_color': '#1f0713',
                'dark_warning_color': '#fbbf24',
                'dark_warning_bg_color': '#1c1305',
                'dark_info_color': '#38bdf8',
                'dark_info_bg_color': '#071926',
                'dark_unknown_color': '#9ca3af',
                'dark_unknown_bg_color': '#1f2937'
            };

            Object.keys(defaultColors).forEach(fieldName => {
                const colorInput = document.getElementById('color-picker-' + fieldName);
                const textInput = document.querySelector('input[name="' + fieldName + '"]');
                
                if (colorInput) {
                    colorInput.value = defaultColors[fieldName];
                }
                if (textInput) {
                    textInput.value = defaultColors[fieldName];
                }
            });

            this.updatePreviews();
        }
    }

    // Initialize color manager
    const colorManager = new ColorManager();

    // Handle enable/disable custom colors
    const enableCustomColorsToggle = document.getElementById('enable_custom_colors_toggle');
    const enableCustomColorsField = document.getElementById('enable_custom_colors');
    const colorSection = document.getElementById('color-customization-section');
    const disabledMessage = document.getElementById('color-disabled-message');
    const statusAlert = document.getElementById('status-alert');
    const statusBadge = document.getElementById('enable-status-badge');
    
    // Initialize toggle state from hidden field
    if (enableCustomColorsToggle && enableCustomColorsField) {
        enableCustomColorsToggle.checked = enableCustomColorsField.checked;
        
        enableCustomColorsToggle.addEventListener('change', function() {
            // Sync with hidden form field
            enableCustomColorsField.checked = this.checked;
            
            if (this.checked) {
                colorSection.classList.remove('opacity-50');
                if (disabledMessage) {
                    disabledMessage.classList.add('d-none');
                }
                
                // Update status alert
                statusAlert.classList.remove('alert-secondary');
                statusAlert.classList.add('alert-success');
                statusAlert.querySelector('i').className = 'bi bi-palette-fill me-2';
                statusAlert.querySelector('span').className = 'text-success';
                statusAlert.querySelector('span').textContent = 'Custom colors are active';
                
                // Update badge
                if (statusBadge) {
                    statusBadge.classList.remove('bg-secondary');
                    statusBadge.classList.add('bg-success');
                    statusBadge.textContent = 'Enabled';
                }
                
                // Re-initialize color previews when enabling
                setTimeout(() => colorManager.updatePreviews(), 100);
                showSaveReminder();
            } else {
                colorSection.classList.add('opacity-50');
                if (disabledMessage) {
                    disabledMessage.classList.remove('d-none');
                }
                
                // Update status alert
                statusAlert.classList.remove('alert-success');
                statusAlert.classList.add('alert-secondary');
                statusAlert.querySelector('i').className = 'bi bi-palette me-2';
                statusAlert.querySelector('span').className = 'text-muted';
                statusAlert.querySelector('span').textContent = 'Using default colors';
                
                // Update badge
                if (statusBadge) {
                    statusBadge.classList.remove('bg-success');
                    statusBadge.classList.add('bg-secondary');
                    statusBadge.textContent = 'Disabled';
                }
                
                showSaveReminder();
            }
        });
    }

    // Function to show save reminder
    function showSaveReminder() {
        const existingReminder = document.querySelector('.save-reminder-alert');
        if (existingReminder) {
            existingReminder.remove();
        }

        const reminder = document.createElement('div');
        reminder.className = 'save-reminder-alert alert alert-info alert-dismissible fade show mt-3';
        reminder.innerHTML = `
            <i class="bi bi-info-circle me-2"></i>
            <strong>Save Required:</strong> Click "Save" to apply the color customization toggle.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const card = colorSection.closest('.card');
        if (card) {
            card.appendChild(reminder);
        }

        setTimeout(() => {
            if (reminder.parentNode) {
                reminder.remove();
            }
        }, 5000);
    }

    // Keyboard navigation support
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey || event.metaKey) {
            if (event.key === 's') {
                event.preventDefault();
                const form = document.getElementById('color-form');
                if (form) {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.click();
                    }
                }
            }
        }
    });

    // Handle reset to defaults button - bypass Bootstrap modal entirely
    const resetButton = document.querySelector('button[data-bs-target="#resetColorsModal"]');
    if (resetButton) {
        // Remove Bootstrap modal attributes to prevent the error
        resetButton.removeAttribute('data-bs-toggle');
        resetButton.removeAttribute('data-bs-target');
        
        // Add our own click handler
        resetButton.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Show a simple confirmation dialog instead of Bootstrap modal
            const confirmReset = confirm('Are you sure you want to reset all color settings to their default values?\n\nThis will restore the original color scheme of the application and disable custom colors.');
            
            if (confirmReset) {
                // Apply default colors to the form
                colorManager.resetToDefaults();
                
                // Show a success message
                showResetSuccessMessage();
            }
        });
    }
    
    // Also handle the modal reset button if someone manages to open the modal
    const resetColorsModal = document.getElementById('resetColorsModal');
    if (resetColorsModal) {
        const modalResetButton = resetColorsModal.querySelector('button[name="reset_colors"]');
        
        if (modalResetButton) {
            modalResetButton.addEventListener('click', function(event) {
                event.preventDefault();
                
                // Apply default colors to the form
                colorManager.resetToDefaults();
                
                // Manually hide the modal
                try {
                    const modal = bootstrap.Modal.getInstance(resetColorsModal);
                    if (modal) {
                        modal.hide();
                    } else {
                        // Fallback: manually hide the modal
                        resetColorsModal.classList.remove('show');
                        resetColorsModal.style.display = 'none';
                        document.body.classList.remove('modal-open');
                        
                        // Remove backdrop if it exists
                        const backdrop = document.querySelector('.modal-backdrop');
                        if (backdrop) {
                            backdrop.remove();
                        }
                    }
                } catch (error) {
                    console.error('Error hiding modal:', error);
                    // Fallback: manually hide the modal
                    resetColorsModal.classList.remove('show');
                    resetColorsModal.style.display = 'none';
                    document.body.classList.remove('modal-open');
                    
                    // Remove backdrop if it exists
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                }
                
                // Show a success message
                showResetSuccessMessage();
            });
        }
    }
    
    // Function to show reset success message
    function showResetSuccessMessage() {
        const existingAlert = document.querySelector('.reset-success-alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        const successAlert = document.createElement('div');
        successAlert.className = 'reset-success-alert alert alert-success alert-dismissible fade show mt-3';
        successAlert.innerHTML = `
            <i class="bi bi-check-circle me-2"></i>
            <strong>Colors Reset:</strong> All color settings have been reset to default values. Click "Save" to apply the changes.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const colorSection = document.getElementById('color-customization-section');
        if (colorSection) {
            colorSection.appendChild(successAlert);
        }

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (successAlert.parentNode) {
                successAlert.remove();
            }
        }, 5000);
    }

    // Refresh CSS after form submission
    const form = document.getElementById('color-form');
    if (form) {
        form.addEventListener('submit', function() {
            setTimeout(() => {
                const customColorsLink = document.getElementById('custom-colors-css');
                if (customColorsLink) {
                    const href = customColorsLink.getAttribute('href');
                    customColorsLink.setAttribute('href', href.split('?')[0] + '?t=' + Date.now());
                }
            }, 500);
        });
    }

    // Additional initialization - ensure all color pickers are properly linked
    setTimeout(() => {
        document.querySelectorAll('.color-input').forEach(colorPicker => {
            const inputGroup = colorPicker.closest('.input-group');
            if (inputGroup) {
                const textInput = inputGroup.querySelector('.hex-input');
                if (textInput && textInput.value) {
                    // Ensure color picker shows the current value
                    colorPicker.value = textInput.value;
                }
            }
        });
    }, 100);
});
