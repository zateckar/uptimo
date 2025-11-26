// Uptimo JavaScript - Configuration and State Management
// This file contains global configuration and application state

// Read timezone from body data attribute
const appTimezone = document.body.getAttribute('data-app-timezone') || 'UTC';

// Make timezone available globally for backward compatibility
window.APP_TIMEZONE = appTimezone;

// Global configuration and state object
window.Uptimo = {
    config: {
        // Auto-refresh disabled by default since SSE handles real-time updates
        autoRefreshInterval: 30000, // 30 seconds (fallback only)
        toastTimeout: 5000,
        sseReconnectDelay: 5000, // 5 seconds
        timezone: appTimezone,
    },
    state: {
        selectedMonitorId: null,
        autoRefreshEnabled: false, // Disabled by default
        sseEnabled: true,
        charts: {},
        currentTimespan: '24h',
    }
};

// Log timezone configuration for debugging
console.log('Configured timezone:', window.APP_TIMEZONE);