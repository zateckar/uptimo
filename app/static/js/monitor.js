// Uptimo JavaScript - Monitor Management
// This file contains monitor-related functionality

// Monitor management
const MonitorManager = {
    // Load monitor details
    loadDetails: function(monitorId) {
        const timespan = Uptimo.state.currentTimespan || '24h';
        
        // Update visual selection state
        this.updateSelectionState(monitorId);
        
        // First load static data from main endpoint
        return Utils.apiRequest(`/dashboard/monitor/${monitorId}`)
            .then(staticData => {
                this.displayDetails(staticData);
                Uptimo.state.selectedMonitorId = monitorId;
                
                // Store monitor data in global state for chart interval detection
                if (!Uptimo.state.monitorData) {
                    Uptimo.state.monitorData = {};
                }
                Uptimo.state.monitorData[monitorId] = staticData.monitor;
                
                // Save selected monitor to cookie for persistence
                MonitorSelectionManager.saveSelectedMonitor(monitorId);
                // Switch SSE to monitor-specific stream
                SSEManager.switchMonitor(monitorId);
                // Clear cache for this monitor to ensure fresh data on first load
                TimespanManager.clearCache(monitorId);
                
                // Then load dynamic check data from specialized endpoints
                return this.loadDynamicData(monitorId, timespan);
            })
            .catch(error => {
                console.error('Error loading monitor details:', error);
                Utils.showToast('Failed to load monitor details', 'danger');
            });
    },
    
    // Load dynamic check data from specialized endpoints
    loadDynamicData: function(monitorId, timespan) {
        // Load chart data
        const chartPromise = Utils.apiRequest(`/dashboard/monitor/${monitorId}/checks?timespan=${timespan}`)
            .then(data => {
                // Convert columnar data to row-based format for compatibility
                const checks = Utils.convertColumnarData(data.checks);
                ChartManager.updateResponseTimeChart(checks, timespan);
                return checks;
            })
            .catch(error => {
                console.error('Error loading chart data:', error);
                return [];
            });
            
        // Load heartbeat data
        const heartbeatPromise = Utils.apiRequest(`/dashboard/monitor/${monitorId}/heartbeat`)
            .then(data => {
                // Convert columnar data to row-based format for compatibility
                const checks = Utils.convertColumnarData(data.checks);
                HeartbeatManager.updateDetailHeartbeat(checks);
                return checks;
            })
            .catch(error => {
                console.error('Error loading heartbeat data:', error);
                return [];
            });
            
        // Return combined promise
        return Promise.all([chartPromise, heartbeatPromise]);
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
        document.getElementById('avgResponseTime24h').textContent =
            Utils.formatResponseTime(monitor.avg_response_time_24h);
        document.getElementById('uptime24h').textContent = `${monitor.uptime_24h || 0}%`;
        document.getElementById('uptime1y').textContent = `${monitor.uptime_1y || 0}%`;
        document.getElementById('uptime7d').textContent = `${monitor.uptime_7d || 0}%`;
        document.getElementById('uptime30d').textContent = `${monitor.uptime_30d || 0}%`;
        
        // Update incidents
        this.updateIncidents(data.incidents);
        
        // Note: Chart and heartbeat data are now loaded separately from specialized endpoints
        // in loadDynamicData() method. This allows for better caching and performance.
        // ChartManager.updateResponseTimeChart() and HeartbeatManager.updateDetailHeartbeat()
        // are called from loadDynamicData() after the main static data is loaded.
        
        // Update SSL and domain information using server-rendered HTML
        // TLS/DNS/domain data is now static (updated once per day) and only included in initial API response
        // SSE updates don't include this data, so we only update if it's explicitly provided
        if (data.hasOwnProperty('tls_html')) {
            // Just insert the server-rendered HTML
            const sslContainer = document.getElementById('sslCertificateInfo');
            const sslSummary = document.getElementById('sslSummaryBody');
            if (sslContainer && data.tls_html) {
                sslContainer.innerHTML = data.tls_html;
            }
            if (sslSummary && data.tls_summary_html) {
                sslSummary.innerHTML = data.tls_summary_html;
            }
            
            const domainContainer = document.getElementById('domainRegistrationInfo');
            const domainSummary = document.getElementById('domainSummaryBody');
            if (domainContainer && data.domain_html) {
                domainContainer.innerHTML = data.domain_html;
            }
            if (domainSummary && data.domain_summary_html) {
                domainSummary.innerHTML = data.domain_summary_html;
            }
            
            const dnsContainer = document.getElementById('dnsInfo');
            const dnsSummary = document.getElementById('dnsSummaryBody');
            if (dnsContainer && data.dns_html) {
                dnsContainer.innerHTML = data.dns_html;
            }
            if (dnsSummary && data.dns_summary_html) {
                dnsSummary.innerHTML = data.dns_summary_html;
            }
            
            // Show the TLS/DNS/Domain section
            const sslDomainSection = document.getElementById('sslDomainSection');
            if (sslDomainSection) {
                sslDomainSection.classList.remove('d-none');
            }
        }
        // Note: If tls_html/domain_html/dns_html are not in data (SSE updates), we don't update these sections
        // This preserves the data that was loaded during initial page load
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
            // Check if we already have this data cached for this monitor
            const monitorId = Uptimo.state.selectedMonitorId;
            
            // Initialize cache structure if needed
            if (!Uptimo.state.checkCache) {
                Uptimo.state.checkCache = {};
            }
            if (!Uptimo.state.checkCache[monitorId]) {
                Uptimo.state.checkCache[monitorId] = {};
            }
            
            // Check if we have cached data for this timespan
            const cachedData = Uptimo.state.checkCache[monitorId][timespan];
            if (cachedData && (Date.now() - cachedData.timestamp) < 60000) { // 1 minute cache
                // Use cached data
                ChartManager.updateResponseTimeChart(cachedData.checks, timespan);
                console.log(`Using cached data for ${timespan}`);
            } else {
                // Fetch fresh data from server
                Utils.apiRequest(`/dashboard/monitor/${monitorId}/checks?timespan=${timespan}`)
                    .then(data => {
                        // Convert columnar data to row-based format for compatibility
                        const checks = Utils.convertColumnarData(data.checks);
                        
                        // Cache the response with timestamp
                        Uptimo.state.checkCache[monitorId][timespan] = {
                            checks: checks,
                            timestamp: Date.now()
                        };
                        
                        ChartManager.updateResponseTimeChart(checks, timespan);
                    })
                    .catch(error => {
                        console.error("Error loading chart data:", error);
                    });
            }
            
            // Reconnect SSE stream to use new timespan
            SSEManager.switchMonitor(monitorId);
        }
    },
    
    // Clear cache for a specific monitor (call when monitor data changes)
    clearCache: function(monitorId) {
        if (Uptimo.state.checkCache && Uptimo.state.checkCache[monitorId]) {
            delete Uptimo.state.checkCache[monitorId];
        }
    },
    
    // Clear all cache (call when switching monitors or on page refresh)
    clearAllCache: function() {
        Uptimo.state.checkCache = {};
    }
};

// Monitor list management
const MonitorListManager = {
    loadHeartbeatData: function(monitorId) {
        Utils.apiRequest(`/dashboard/monitor/${monitorId}/heartbeat`)
            .then(data => {
                // Convert columnar data to row-based format for compatibility
                const checks = Utils.convertColumnarData(data.checks);
                HeartbeatManager.updateSidebarHeartbeat(monitorId, checks);
            })
            .catch(error => {
                console.error(`Error loading heartbeat for monitor ${monitorId}:`, error);
            });
    }
};