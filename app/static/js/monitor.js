// Uptimo JavaScript - Monitor Management
// This file contains monitor-related functionality

// Monitor management
const MonitorManager = {
    // Load monitor details
    loadDetails: function(monitorId) {
        const timespan = Uptimo.state.currentTimespan || '24h';
        
        // Update visual selection state
        this.updateSelectionState(monitorId);
        
        return Utils.apiRequest(`/dashboard/monitor/${monitorId}?timespan=${timespan}`)
            .then(data => {
                this.displayDetails(data);
                Uptimo.state.selectedMonitorId = monitorId;
                // Save selected monitor to cookie for persistence
                MonitorSelectionManager.saveSelectedMonitor(monitorId);
                // Switch SSE to monitor-specific stream
                SSEManager.switchMonitor(monitorId);
                return data;
            })
            .catch(error => {
                console.error('Error loading monitor details:', error);
                Utils.showToast('Failed to load monitor details', 'danger');
            });
    },
    
    // Update visual selection state in sidebar
    updateSelectionState: function(monitorId) {
        // Remove active class from all monitors
        document.querySelectorAll('.monitor-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to selected monitor
        const selectedItem = document.querySelector(
            `.monitor-item[data-monitor-id="${monitorId}"]`
        );
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
    },
    
    // Display monitor details
    displayDetails: function(data) {
        const monitor = data.monitor;
        
        // Hide welcome, show details
        document.getElementById('welcomeMessage').classList.add('d-none');
        document.getElementById('monitorDetails').classList.remove('d-none');
        
        // Update header
        document.getElementById('monitorTitle').textContent = monitor.name;
        document.getElementById('monitorTarget').textContent = `${monitor.type.toUpperCase()}: ${monitor.target}`;
        
        // Update status
        const statusEl = document.getElementById('monitorStatus');
        statusEl.textContent = monitor.last_status.toUpperCase();
        statusEl.className = 'badge fs-6 ' + Utils.getStatusBadgeClass(monitor.last_status);
        
        // Update last check time
        if (monitor.last_check) {
            document.getElementById('lastCheckTime').textContent = 
                `Last check: ${Utils.formatDateTime(monitor.last_check)}`;
        }
        
        // Update action buttons with server-rendered HTML
        if (data.action_buttons_html) {
            this.updateActionButtons(data.action_buttons_html);
        }
        
        // Update stats
        document.getElementById('currentResponseTime').textContent =
            Utils.formatResponseTime(monitor.last_response_time);
        document.getElementById('uptime24h').textContent = `${monitor.uptime_24h}%`;
        document.getElementById('uptime7d').textContent = `${monitor.uptime_7d}%`;
        document.getElementById('uptime30d').textContent = `${monitor.uptime_30d}%`;
        
        // Update incidents
        this.updateIncidents(data.incidents);
        
        // Update chart with current timespan
        ChartManager.updateResponseTimeChart(data.recent_checks, Uptimo.state.currentTimespan);
        
        // Update heartbeat - use heartbeat_checks if available, otherwise recent_checks
        // heartbeat_checks are now explicitly provided by the API for the detail view
        const heartbeatData = data.heartbeat_checks || data.recent_checks;
        HeartbeatManager.updateDetailHeartbeat(heartbeatData);
        
        // Update SSL and domain information
        // Use explicit data from API if available, otherwise fallback to recent checks (backward compatibility)
        if (data.ssl_info || data.domain_info || data.dns_info) {
            SSLDomainManager.updateSSLAndDomainInfoFromData(data.monitor, data.ssl_info, data.domain_info, data.dns_info);
        } else {
            SSLDomainManager.updateSSLAndDomainInfo(data.monitor, data.recent_checks);
        }
    },
    
    // Update action buttons with server-rendered HTML
    updateActionButtons: function(actionButtonsHtml) {
        const actionsContainer = document.getElementById('monitorActions');
        // Simply insert the server-rendered HTML
        actionsContainer.innerHTML = actionButtonsHtml;
        
        // Set up event delegation for toggle buttons
        const toggleBtn = actionsContainer.querySelector('[data-toggle-form]');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                const formId = this.getAttribute('data-toggle-form');
                const form = document.getElementById(formId);
                if (form) {
                    form.submit();
                }
            });
        }
    },
    
    // Update outages list (formerly incidents)
    updateIncidents: function(incidents) {
        const container = document.getElementById('incidentsList');
        
        if (incidents.length === 0) {
            container.innerHTML = '<div class="text-muted">No outages recorded</div>';
            return;
        }
        
        const html = incidents.map(incident => `
            <div class="alert alert-${incident.is_active ? 'danger' : 'info'} mb-2 py-2 incident-${incident.is_active ? 'active' : 'resolved'} position-relative">
                <div class="small incident-content-padding">
                    <strong>${incident.is_active ? '🔴 Active' : '🟢 Resolved'}</strong>
                    <span class="text-muted ms-2">${Utils.formatDateTime(incident.started_at)}</span>
                    ${incident.resolved_at ? `<span class="text-muted ms-2">→ ${Utils.formatDateTime(incident.resolved_at)}</span>` : ''}
                    ${incident.description ? `: <span class="text-danger">  ⚠ ${incident.description}</span>` : ''}
                </div>
                <span class="badge text-lowercase bg-dark fs-6 position-absolute top-50 end-0 translate-middle-y me-2">${Utils.formatDuration(incident.duration)}</span>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
};

// Timespan manager
const TimespanManager = {
    changeTimespan: function(timespan) {
        Uptimo.state.currentTimespan = timespan;
        
        // Update button states
        document.querySelectorAll(".timespan-btn").forEach(btn => {
            btn.classList.remove("active", "btn-secondary");
            btn.classList.add("btn-outline-secondary");
        });
        
        const activeBtn = document.querySelector(`[data-timespan="${timespan}"]`);
        if (activeBtn) {
            activeBtn.classList.remove("btn-outline-secondary");
            activeBtn.classList.add("active", "btn-secondary");
        }
        
        // Refresh chart if monitor is selected
        if (Uptimo.state.selectedMonitorId) {
            Utils.apiRequest(`/dashboard/monitor/${Uptimo.state.selectedMonitorId}/checks?timespan=${timespan}`)
                .then(data => {
                    ChartManager.updateResponseTimeChart(data.checks, timespan);
                })
                .catch(error => {
                    console.error("Error loading chart data:", error);
                });
            
            // Reconnect SSE stream to use new timespan
            SSEManager.switchMonitor(Uptimo.state.selectedMonitorId);
        }
    }
};

// Monitor list management
const MonitorListManager = {
    loadHeartbeatData: function(monitorId) {
        Utils.apiRequest(`/dashboard/monitor/${monitorId}/heartbeat`)
            .then(data => {
                HeartbeatManager.updateSidebarHeartbeat(monitorId, data.checks);
            })
            .catch(error => {
                console.error(`Error loading heartbeat for monitor ${monitorId}:`, error);
            });
    }
};