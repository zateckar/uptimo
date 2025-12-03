/**
 * Notification Channels JavaScript
 * Handles dynamic form behavior for notification channel creation and editing
 */

class NotificationChannelForm {
    constructor() {
        this.channelTypeSelect = null;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupForm());
        } else {
            this.setupForm();
        }
    }

    setupForm() {
        this.channelTypeSelect = document.getElementById('channelType');
        if (!this.channelTypeSelect) return;

        // Show appropriate config on change
        this.channelTypeSelect.addEventListener('change', () => {
            this.showConfigForType(this.channelTypeSelect.value);
        });

        // Show config for currently selected value on page load
        if (this.channelTypeSelect.value) {
            this.showConfigForType(this.channelTypeSelect.value);
        } else {
            this.hideAllConfigs();
            this.hideAllHelp();
            this.showElement('defaultHelp');
        }
    }

    showConfigForType(type) {
        this.hideAllConfigs();
        this.hideAllHelp();
        
        switch(type) {
            case 'email':
                this.showElement('emailConfig');
                this.showElement('emailHelp');
                break;
            case 'telegram':
                this.showElement('telegramConfig');
                this.showElement('telegramHelp');
                break;
            case 'slack':
                this.showElement('slackConfig');
                this.showElement('slackHelp');
                break;
        }
    }

    hideAllConfigs() {
        this.hideElement('emailConfig');
        this.hideElement('telegramConfig');
        this.hideElement('slackConfig');
    }

    hideAllHelp() {
        this.hideElement('emailHelp');
        this.hideElement('telegramHelp');
        this.hideElement('slackHelp');
        this.hideElement('defaultHelp');
    }

    showElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('d-none');
        }
    }

    hideElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add('d-none');
        }
    }
}

// Initialize when loaded
new NotificationChannelForm();
