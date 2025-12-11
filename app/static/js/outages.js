// Uptimo JavaScript - Outages Management
// This file contains functionality for managing the outages list

const OutagesManager = {
    currentFilter: 'all',
    incidents: [],
    
    // Initialize outages list
    initialize: function() {
        this.setupEventListeners();
        this.loadOutages();
    },
    
    // Setup event listeners
    setupEventListeners: function() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.changeFilter(e.target.dataset.filter);
            });
        });
    },
    
    // Load outages from API
    loadOutages: async function() {
        try {
            const response = await fetch('/dashboard/incidents');
            const data = await response.json();
            this.incidents = data.incidents;
            this.renderOutages();
            this.updateStats(data.unseen_count);
            
            // Mark all currently visible incidents as viewed after a delay
            setTimeout(() => this.markVisibleAsViewed(), 2000);
        } catch (error) {
            console.error('Error loading outages:', error);
            this.showError();
        }
    },
    
    // Render outages list
    renderOutages: function() {
        const container = document.getElementById('outagesList');
        if (!container) return;
        
        const filteredIncidents = this.getFilteredIncidents();
        
        if (filteredIncidents.length === 0) {
            container.innerHTML = `
                <div class="text-center p-5 text-muted">
                    <i class="bi bi-check-circle mb-2 d-block icon-size-2rem"></i>
                    <p class="small">No outages found</p>
                </div>
            `;
            return;
        }
        
        const incidentsHtml = filteredIncidents.map(incident => this.renderIncident(incident)).join('');
        container.innerHTML = incidentsHtml;
    },
    
    // Render single incident
    renderIncident: function(incident) {
        const isNew = !incident.is_viewed;
        const isActive = incident.status === 'active';
        const alertClass = isNew ? 'alert-warning' : (isActive ? 'alert-danger' : 'alert-info'); // Changed to alert-info for better dark mode visibility
        const newBadge = isNew ? '<span class="badge bg-warning ms-2">NEW</span>' : '';
        
        return `
            <div class="alert ${alertClass} incident-item p-2 mb-2 incident-${isActive ? 'active' : 'resolved'} position-relative" data-incident-id="${incident.id}">
                <div class="small incident-content-padding">
                    <strong>${isActive ? '🔴' : '🟢'}</strong>
                    <span class="text-bold ms-2">${incident.monitor_name || `Monitor #${incident.monitor_id}`}</span>
                    <span class="text-muted ms-2">${this.formatDateTime(incident.started_at)}</span>
                    ${incident.resolved_at ? `<span class="text-muted ms-2">→ ${this.formatDateTime(incident.resolved_at)}</span>` : ''}
                    ${incident.description ? ` : <span class="text-danger">⚠ ${incident.description}</span>` : ''}
                    ${newBadge}
                </div>
                <div class="position-absolute top-50 end-0 translate-middle-y me-2 d-flex align-items-center gap-2">
                    <span class="badge text-lowercase bg-dark">${incident.duration_formatted}</span>
                    ${isActive ? `
                        <button class="btn btn-sm btn-outline-light" onclick="OutagesManager.resolveIncident(${incident.id})" title="Resolve Incident">
                            <i class="bi bi-check-lg"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
    // Format date time (reuse from utils if available)
    formatDateTime: function(dateString) {
        if (typeof Utils !== 'undefined' && Utils.formatDateTime) {
            return Utils.formatDateTime(dateString);
        }
        // Fallback implementation
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            month: '2-digit',
            day: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).replace(',', '');
    },
    
    // Get filtered incidents based on current filter
    getFilteredIncidents: function() {
        switch (this.currentFilter) {
            case 'unseen':
                return this.incidents.filter(i => !i.is_viewed);
            case 'active':
                return this.incidents.filter(i => i.status === 'active');
            default:
                return this.incidents;
        }
    },
    
    // Change filter
    changeFilter: function(filter) {
        this.currentFilter = filter;
        
        // Update button states
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active', 'btn-primary');
            btn.classList.add('btn-outline-secondary');
        });
        
        const activeBtn = document.querySelector(`[data-filter="${filter}"]`);
        activeBtn.classList.remove('btn-outline-secondary');
        activeBtn.classList.add('active', 'btn-primary');
        
        this.renderOutages();
    },
    
    // Mark visible incidents as viewed
    markVisibleAsViewed: async function() {
        const visibleIncidents = document.querySelectorAll('.incident-item[data-incident-id]');
        const unseenIncidents = Array.from(visibleIncidents).filter(el => {
            const incidentId = parseInt(el.dataset.incidentId);
            const incident = this.incidents.find(i => i.id === incidentId);
            return incident && !incident.is_viewed;
        });
        
        if (unseenIncidents.length === 0) return;
        
        // Get CSRF token from meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // Mark each unseen incident as viewed
        const promises = unseenIncidents.map(el => {
            const incidentId = parseInt(el.dataset.incidentId);
            return fetch(`/dashboard/incidents/${incidentId}/view`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
        });
        
        try {
            await Promise.all(promises);
            // Update local state
            unseenIncidents.forEach(el => {
                const incidentId = parseInt(el.dataset.incidentId);
                const incident = this.incidents.find(i => i.id === incidentId);
                if (incident) incident.is_viewed = true;
            });
            this.renderOutages();
            this.updateStats(0);
        } catch (error) {
            console.error('Error marking incidents as viewed:', error);
        }
    },
    
    // Update statistics
    updateStats: function(unseenCount) {
        const statsEl = document.getElementById('outageStats');
        if (statsEl) {
            const totalActive = this.incidents.filter(i => i.status === 'active').length;
            let text = `${this.incidents.length} total incidents`;
            if (totalActive > 0) {
                text += ` • ${totalActive} active`;
            }
            if (unseenCount > 0) {
                text += ` • ${unseenCount} new`;
            }
            statsEl.textContent = text;
        }
    },
    
    // Show error message
    showError: function() {
        const container = document.getElementById('outagesList');
        if (container) {
            container.innerHTML = `
                <div class="text-center p-5 text-muted">
                    <i class="bi bi-exclamation-triangle mb-2 d-block icon-size-2rem"></i>
                    <p class="small">Failed to load outages. Please try again.</p>
                    <button class="btn btn-sm btn-outline-secondary" id="retryOutagesBtn">
                        Retry
                    </button>
                </div>
            `;
            
            // Add event listener to the retry button
            const retryBtn = document.getElementById('retryOutagesBtn');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => this.loadOutages());
            }
        }
    },
    
    // Refresh outages list
    refresh: function() {
        this.loadOutages();
    },
    
    // Show outages container (when no monitor is selected)
    show: function() {
        const outagesContainer = document.getElementById('outagesListContainer');
        const welcomeMessage = document.getElementById('welcomeMessage');
        const monitorDetails = document.getElementById('monitorDetails');
        
        if (outagesContainer && welcomeMessage && monitorDetails) {
            // Check if there are monitors
            const monitorItems = document.querySelectorAll('.monitor-item[data-monitor-id]');
            
            if (monitorItems.length > 0) {
                // Has monitors - show outages list
                welcomeMessage.classList.add('d-none');
                monitorDetails.classList.add('d-none');
                outagesContainer.classList.remove('d-none');
                
                // Load outages if not already loaded
                if (this.incidents.length === 0) {
                    this.loadOutages();
                }
            } else {
                // No monitors - show welcome message
                outagesContainer.classList.add('d-none');
                monitorDetails.classList.add('d-none');
                welcomeMessage.classList.remove('d-none');
            }
        }
    },
    
    // Hide outages container (when a monitor is selected)
    hide: function() {
        const outagesContainer = document.getElementById('outagesListContainer');
        const monitorDetails = document.getElementById('monitorDetails');
        const welcomeMessage = document.getElementById('welcomeMessage');
        
        if (outagesContainer && monitorDetails && welcomeMessage) {
            outagesContainer.classList.add('d-none');
            welcomeMessage.classList.add('d-none');
            monitorDetails.classList.remove('d-none');
        }
    },
    
    // Resolve incident
    resolveIncident: async function(incidentId) {
        // Get CSRF token from meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        try {
            const response = await fetch(`/dashboard/incidents/${incidentId}/resolve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                // Update local incident data
                const incident = this.incidents.find(i => i.id === incidentId);
                if (incident) {
                    incident.status = 'resolved';
                    incident.resolved_at = data.resolved_at;
                    incident.duration_formatted = data.duration_formatted || 'N/A';
                }
                // Re-render the outages list
                this.renderOutages();
            } else {
                const errorData = await response.json();
                console.error('Error resolving incident:', errorData.error);
                // Show error message to user
                this.showNotification('Failed to resolve incident: ' + (errorData.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error resolving incident:', error);
            this.showNotification('Failed to resolve incident. Please try again.', 'error');
        }
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        // Create a simple notification (you can enhance this)
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Make OutagesManager globally available
    window.OutagesManager = OutagesManager;
});