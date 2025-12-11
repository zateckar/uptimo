// Uptimo JavaScript - Utility Functions and Theme Management
// This file contains utility functions and the theme manager

// Theme management
const ThemeManager = {
    // Initialize theme from cookie or system preference
    init: function() {
        const savedTheme = this.getThemeFromCookie();
        const systemPreference = this.getSystemThemePreference();
        
        // Use saved theme if available, otherwise use system preference
        const theme = savedTheme || systemPreference;
        this.setTheme(theme);
    },
    
    // Get theme from cookie
    getThemeFromCookie: function() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'uptimo_theme') {
                return decodeURIComponent(value);
            }
        }
        return null;
    },
    
    // Save theme to cookie
    saveThemeToCookie: function(theme) {
        const expires = new Date();
        expires.setFullYear(expires.getFullYear() + 1); // 1 year expiry
        document.cookie = `uptimo_theme=${encodeURIComponent(theme)}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
    },
    
    // Get system theme preference
    getSystemThemePreference: function() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    },
    
    // Set theme
    setTheme: function(theme) {
        const htmlElement = document.documentElement;
        const themeIcon = document.getElementById('themeIcon');
        
        if (theme === 'dark') {
            htmlElement.setAttribute('data-theme', 'dark');
            if (themeIcon) {
                themeIcon.className = 'bi bi-moon-fill';
            }
        } else {
            htmlElement.removeAttribute('data-theme');
            if (themeIcon) {
                themeIcon.className = 'bi bi-sun-fill';
            }
        }
        
        // Save to cookie
        this.saveThemeToCookie(theme);
    },
    
    // Toggle theme
    toggle: function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }
};

// Monitor selection management (cookie-based persistence)
const MonitorSelectionManager = {
    // Get last selected monitor from cookie
    getLastSelectedMonitor: function() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'uptimo_selected_monitor') {
                const monitorId = decodeURIComponent(value);
                return monitorId ? parseInt(monitorId) : null;
            }
        }
        return null;
    },
    
    // Save selected monitor to cookie
    saveSelectedMonitor: function(monitorId) {
        const expires = new Date();
        expires.setFullYear(expires.getFullYear() + 1); // 1 year expiry
        document.cookie = (
            `uptimo_selected_monitor=${encodeURIComponent(monitorId)}; ` +
            `expires=${expires.toUTCString()}; path=/; SameSite=Lax`
        );
    },
    
    // Clear selected monitor cookie
    clearSelectedMonitor: function() {
        document.cookie = (
            'uptimo_selected_monitor=; expires=Thu, 01 Jan 1970 00:00:00 UTC; ' +
            'path=/; SameSite=Lax'
        );
    }
};

// Utility functions
const Utils = {
    // Format date/time using server's configured timezone
    formatDateTime: function(dateString) {
        const date = new Date(dateString);
        const timezone = window.APP_TIMEZONE || 'UTC';
        
        try {
            // Format with the server's configured timezone
            return date.toLocaleString('en-US', {
                timeZone: timezone,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (e) {
            // Fallback to UTC if timezone is invalid
            console.warn(`Invalid timezone '${timezone}', falling back to UTC`);
            return date.toLocaleString('en-US', {
                timeZone: 'UTC',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        }
    },
    
    // Format duration in seconds to human readable format
    formatDuration: function(seconds) {
        if (!seconds) return 'N/A';
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },
    
    // Format response time with appropriate unit
    formatResponseTime: function(ms) {
        if (!ms) return '--';
        
        if (ms < 1000) {
            return `${Math.round(ms)}ms`;
        } else {
            return `${(ms / 1000).toFixed(2)}s`;
        }
    },
    
    // Get status color class
    getStatusClass: function(status) {
        switch (status) {
            case 'up': return 'text-success';
            case 'down': return 'text-danger';
            case 'unknown': return 'text-secondary';
            default: return 'text-muted';
        }
    },
    
    // Get status badge class
    getStatusBadgeClass: function(status) {
        switch (status) {
            case 'up': return 'bg-success';
            case 'down': return 'bg-danger';
            case 'unknown': return 'bg-secondary';
            default: return 'bg-secondary';
        }
    },
    
    // Show toast notification
    showToast: function(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: Uptimo.config.toastTimeout
        });
        
        bsToast.show();
        
        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },
    
    // Create toast container if it doesn't exist
    createToastContainer: function() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3 toast-container-zindex-1050';
        document.body.appendChild(container);
        return container;
    },
    
    // Make API request
    apiRequest: function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        return fetch(url, finalOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            });
    },
    
    // Get CSRF token from meta tag
    getCSRFToken: function() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.content : '';
    },
    
    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Update favicon based on monitor statuses (now handled by backend)
    // The backend /favicon.ico route handles favicon updates based on real-time status
    updateFavicon: function(monitors) {
        // Favicon is now handled by the backend /favicon.ico route
        // We trigger a refresh only when the status actually changes
        let hasDown = false;
        let hasUnknown = false;
        
        if (monitors && Object.keys(monitors).length > 0) {
            hasDown = Object.values(monitors).some(
                m => m.is_active && m.last_status === 'down'
            );
            hasUnknown = Object.values(monitors).some(
                m => m.is_active && m.last_status === 'unknown'
            );
        }
        
        // Determine expected favicon based on current status
        let expectedFavicon = 'favicon-up.svg';
        if (hasDown) {
            expectedFavicon = 'favicon-down.svg';
        } else if (hasUnknown) {
            expectedFavicon = 'favicon-warning.svg';
        }
        
        // Only trigger refresh if we think the favicon should be different
        // This minimizes unnecessary favicon requests
        if (!Utils._lastKnownFaviconStatus || Utils._lastKnownFaviconStatus !== expectedFavicon) {
            Utils._lastKnownFaviconStatus = expectedFavicon;
            
            // Force browser to request /favicon.ico again by adding cache-busting
            const links = document.querySelectorAll('link[rel*="icon"]');
            links.forEach(link => {
                link.href = '/favicon.ico?v=' + Date.now().toString();
            });
            
            console.log(`Triggered favicon refresh for status: ${expectedFavicon}`);
        }
    },
    
    // Track the last known favicon status to minimize refreshes
    _lastKnownFaviconStatus: null,
    
    // Convert columnar data format back to traditional row-based format
    // This handles both the old full columnar format and the new minimal chart format
    convertColumnarData: function(columnarData) {
        // Check if data is already in row-based format (legacy compatibility)
        if (Array.isArray(columnarData)) {
            return columnarData;
        }
        
        if (!columnarData || typeof columnarData !== 'object') {
            return [];
        }
        
        // Check if this is the new minimal chart format: {t: [...], r: [...], s: [...], c: [...], e: [...]}
        if (columnarData.t && Array.isArray(columnarData.t)) {
            const objects = [];
            for (let i = 0; i < columnarData.t.length; i++) {
                objects.push({
                    t: columnarData.t[i],      // timestamp - keep short name for compatibility with charts.js
                    r: columnarData.r[i],      // response_time - keep short name for compatibility with charts.js
                    s: columnarData.s[i],      // status - keep short name for compatibility with charts.js
                    c: columnarData.c[i],      // status_code - keep short name for compatibility with charts.js
                    e: columnarData.e[i]       // error_message - keep short name for compatibility with charts.js
                });
            }
            return objects;
        }
        
        // Check if this is the old full columnar format (has column arrays with long names)
        if (columnarData.ids && Array.isArray(columnarData.ids)) {
            const ids = columnarData.ids || [];
            const monitorIds = columnarData.monitor_ids || [];
            const timestamps = columnarData.timestamps || [];
            const statuses = columnarData.statuses || [];
            const responseTimes = columnarData.response_times || [];
            const statusCodes = columnarData.status_codes || [];
            const errorMessages = columnarData.error_messages || [];
            const additionalData = columnarData.additional_data || [];
            const isSuccesses = columnarData.is_successes || [];
            const isTimeouts = columnarData.is_timeouts || [];
            const isCertificateErrors = columnarData.is_certificate_errors || [];
            
            // Convert to row-based format
            const rowData = [];
            const length = Math.max(
                ids.length, monitorIds.length, timestamps.length, statuses.length,
                responseTimes.length, statusCodes.length, errorMessages.length,
                additionalData.length, isSuccesses.length, isTimeouts.length,
                isCertificateErrors.length
            );
            
            for (let i = 0; i < length; i++) {
                rowData.push({
                    id: ids[i],
                    monitor_id: monitorIds[i],
                    timestamp: timestamps[i],
                    status: statuses[i],
                    response_time: responseTimes[i],
                    status_code: statusCodes[i],
                    error_message: errorMessages[i],
                    additional_data: additionalData[i],
                    is_success: isSuccesses[i],
                    is_timeout: isTimeouts[i],
                    is_certificate_error: isCertificateErrors[i]
                });
            }
            
            return rowData;
        }
        
        // Unknown format
        return [];
    }
};

// Initialize theme on page load (for all users, authenticated or not)
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme from saved preference or system default
    ThemeManager.init();
    
    // Setup theme toggle button if it exists
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            ThemeManager.toggle();
        });
    }
});