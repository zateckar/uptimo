// Uptimo JavaScript - Real-time Updates (SSE)
// This file contains Server-Sent Events management for real-time updates

// Server-Sent Events manager for real-time updates
const SSEManager = {
    eventSource: null,
    monitorEventSource: null,
    reconnectTimeouts: {
        dashboard: null,
        monitor: null
    },
    connectionState: {
        dashboard: 'disconnected',
        monitor: 'disconnected'
    },
    maxReconnectAttempts: 10,
    reconnectAttempts: {
        dashboard: 0,
        monitor: 0
    },
    
    // Initialize SSE connections
    initialize: function() {
        if (!Uptimo.state.sseEnabled) {
            console.log('SSE is disabled');
            return;
        }
        
        // Reset connection states
        this.connectionState.dashboard = 'connecting';
        this.connectionState.monitor = 'disconnected';
        this.reconnectAttempts.dashboard = 0;
        this.reconnectAttempts.monitor = 0;
        
        // Connect to general dashboard stream
        this.connectDashboardStream();
        
        // Connect to specific monitor stream if one is selected
        if (Uptimo.state.selectedMonitorId) {
            this.connectMonitorStream(Uptimo.state.selectedMonitorId);
        }
    },
    
    // Connect to dashboard stream for all monitors
    connectDashboardStream: function() {
        // Clear any existing reconnection timeout
        if (this.reconnectTimeouts.dashboard) {
            clearTimeout(this.reconnectTimeouts.dashboard);
            this.reconnectTimeouts.dashboard = null;
        }
        
        // Close existing connection if any
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        this.connectionState.dashboard = 'connecting';
        
        try {
            console.log('Attempting to connect to dashboard SSE stream...');
            this.eventSource = new EventSource('/dashboard/stream', {
                withCredentials: true
            });
            
            this.eventSource.onopen = () => {
                console.log('SSE connection established for dashboard');
                this.connectionState.dashboard = 'connected';
                this.reconnectAttempts.dashboard = 0;
            };
            
            this.eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleDashboardUpdate(data);
                } catch (error) {
                    console.error('Error parsing SSE data:', error);
                }
            };
            
            this.eventSource.onerror = (error) => {
                console.error('SSE connection error for dashboard:', error);
                this.connectionState.dashboard = 'error';
                
                // Close the broken connection
                if (this.eventSource) {
                    this.eventSource.close();
                    this.eventSource = null;
                }
                
                // Attempt to reconnect with exponential backoff
                this.scheduleReconnect('dashboard');
            };
        } catch (error) {
            console.error('Failed to create SSE connection:', error);
            this.connectionState.dashboard = 'error';
            Utils.showToast('Failed to establish real-time connection', 'danger');
            this.scheduleReconnect('dashboard');
        }
    },
    
    // Connect to specific monitor stream
    connectMonitorStream: function(monitorId) {
        // Clear any existing reconnection timeout
        if (this.reconnectTimeouts.monitor) {
            clearTimeout(this.reconnectTimeouts.monitor);
            this.reconnectTimeouts.monitor = null;
        }
        
        // Close existing connection if any
        if (this.monitorEventSource) {
            this.monitorEventSource.close();
            this.monitorEventSource = null;
        }
        
        this.connectionState.monitor = 'connecting';
        
        try {
            // Build URL with timespan parameter
            const timespan = Uptimo.state.currentTimespan || '24h';
            const streamUrl = `/dashboard/monitor/${monitorId}/stream?timespan=${timespan}`;
            
            console.log(`Attempting to connect to monitor ${monitorId} SSE stream with timespan ${timespan}...`);
            this.monitorEventSource = new EventSource(streamUrl, {
                withCredentials: true
            });
            
            this.monitorEventSource.onopen = () => {
                console.log(`SSE connection established for monitor ${monitorId}`);
                this.connectionState.monitor = 'connected';
                this.reconnectAttempts.monitor = 0;
            };
            
            this.monitorEventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMonitorUpdate(data);
                } catch (error) {
                    console.error('Error parsing monitor SSE data:', error);
                }
            };
            
            this.monitorEventSource.onerror = (error) => {
                console.error(`SSE connection error for monitor ${monitorId}:`, error);
                this.connectionState.monitor = 'error';
                
                // Close the broken connection
                if (this.monitorEventSource) {
                    this.monitorEventSource.close();
                    this.monitorEventSource = null;
                }
                
                // Attempt to reconnect with exponential backoff
                this.scheduleReconnect('monitor', monitorId);
            };
        } catch (error) {
            console.error('Failed to create monitor SSE connection:', error);
            this.connectionState.monitor = 'error';
            this.scheduleReconnect('monitor', monitorId);
        }
    },
    
    // Schedule reconnection with exponential backoff
    scheduleReconnect: function(type, monitorId = null) {
        const attemptsKey = type;
        const maxAttempts = this.maxReconnectAttempts;
        
        if (this.reconnectAttempts[attemptsKey] >= maxAttempts) {
            console.error(`Max reconnection attempts (${maxAttempts}) reached for ${type} SSE`);
            Utils.showToast(
                `Real-time connection failed after ${maxAttempts} attempts`,
                'danger'
            );
            this.connectionState[type] = 'failed';
            return;
        }
        
        this.reconnectAttempts[attemptsKey]++;
        
        // Exponential backoff: 5s, 10s, 20s, 40s, 60s, 60s, ...
        const baseDelay = 5000; // 5 seconds
        const maxDelay = 60000; // 60 seconds
        const delay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts[attemptsKey] - 1), maxDelay);
        
        console.log(
            `Scheduling reconnection attempt ${this.reconnectAttempts[attemptsKey]} for ${type} SSE in ${delay/1000}s`
        );
        
        this.reconnectTimeouts[type] = setTimeout(() => {
            if (Uptimo.state.sseEnabled) {
                if (type === 'dashboard') {
                    this.connectDashboardStream();
                } else if (type === 'monitor' && monitorId && Uptimo.state.selectedMonitorId === monitorId) {
                    this.connectMonitorStream(monitorId);
                }
            }
        }, delay);
    },
    
    // Handle dashboard updates from SSE
    handleDashboardUpdate: function(data) {
        // Update global stats
        if (data.stats) {
            this.updateGlobalStats(data.stats);
        }
        
        // Update monitor data
        if (data.monitors) {
            Object.keys(data.monitors).forEach(monitorId => {
                const monitorData = data.monitors[monitorId];
                this.updateMonitorInList(monitorId, monitorData);
                // Only update heartbeat if this monitor is NOT currently selected
                // to prevent conflicts with the monitor-specific stream
                if (monitorData.recent_checks &&
                    monitorData.recent_checks.length > 0 &&
                    Uptimo.state.selectedMonitorId !== parseInt(monitorId)) {
                    this.updateMonitorHeartbeat(monitorId, monitorData.recent_checks);
                }
            });
            
            // Update favicon based on current monitor statuses
            Utils.updateFavicon(data.monitors);
        }
    },
    
    // Handle specific monitor updates from SSE
    handleMonitorUpdate: function(data) {
        if (data.monitor) {
            // Update detail view if this monitor is selected
            if (Uptimo.state.selectedMonitorId === data.monitor.id) {
                // Create a safe data object with default empty arrays
                // Include ssl_info, domain_info, dns_info if available
                const safeData = {
                    monitor: data.monitor,
                    recent_checks: data.recent_checks || [],
                    heartbeat_checks: data.heartbeat_checks || data.recent_checks || [],
                    incidents: data.incidents || [],
                    ssl_info: data.ssl_info || null,
                    domain_info: data.domain_info || null,
                    dns_info: data.dns_info || null
                };
                MonitorManager.displayDetails(safeData);
            }
            
            // Update heartbeat in sidebar - use heartbeat_checks if available, otherwise recent_checks
            const heartbeatData = data.heartbeat_checks || data.recent_checks;
            if (heartbeatData) {
                HeartbeatManager.updateSidebarHeartbeat(data.monitor.id, heartbeatData);
            }
        }
    },
    
    // Update global statistics
    updateGlobalStats: function(stats) {
        const upMonitorsEl = document.getElementById('upMonitors');
        const downMonitorsEl = document.getElementById('downMonitors');
        const activeIncidentsEl = document.getElementById('activeIncidents');
        
        if (upMonitorsEl) upMonitorsEl.textContent = stats.up_monitors || 0;
        if (downMonitorsEl) downMonitorsEl.textContent = stats.down_monitors || 0;
        if (activeIncidentsEl) activeIncidentsEl.textContent = stats.active_incidents || 0;
    },
    
    // Update monitor in the sidebar list
    updateMonitorInList: function(monitorId, monitorData) {
        const monitorItem = document.querySelector(`[data-monitor-id="${monitorId}"]`);
        if (!monitorItem) return;
        
        // Update status badge with uptime percentage
        const statusBadge = monitorItem.querySelector('.badge');
        if (statusBadge) {
            statusBadge.textContent = `${monitorData.uptime_24h}%`;
            statusBadge.className = `badge ${Utils.getStatusBadgeClass(monitorData.last_status)}`;
        }
        
        // Update response time
        const responseTimeContainer = monitorItem.querySelector('.d-flex.w-100.justify-content-between.mt-1');
        if (responseTimeContainer && monitorData.last_response_time) {
            const existingTimeElement = responseTimeContainer.querySelector('small');
            if (existingTimeElement) {
                existingTimeElement.textContent = Utils.formatResponseTime(monitorData.last_response_time);
            }
        }
    },
    
    // Update monitor heartbeat
    updateMonitorHeartbeat: function(monitorId, recentChecks) {
        // Only update if we have valid recent checks
        if (recentChecks && recentChecks.length > 0) {
            HeartbeatManager.updateSidebarHeartbeat(monitorId, recentChecks);
        }
    },
    
    // Switch monitor stream when selecting a different monitor
    switchMonitor: function(monitorId) {
        // Clear any pending monitor reconnection
        if (this.reconnectTimeouts.monitor) {
            clearTimeout(this.reconnectTimeouts.monitor);
            this.reconnectTimeouts.monitor = null;
        }
        
        if (monitorId) {
            this.reconnectAttempts.monitor = 0;
            this.connectMonitorStream(monitorId);
        } else {
            // Close monitor stream when deselecting
            if (this.monitorEventSource) {
                this.monitorEventSource.close();
                this.monitorEventSource = null;
            }
            this.connectionState.monitor = 'disconnected';
            
            // Request immediate dashboard update to restore heartbeat updates
            // for all monitors when deselecting
            this.requestDashboardUpdate();
        }
    },
    
    // Request immediate dashboard update
    requestDashboardUpdate: function() {
        // Force dashboard stream to send current state immediately
        // This ensures heartbeat updates resume for all monitors
        Utils.apiRequest('/dashboard/overview-stats')
            .then(data => {
                console.log('Dashboard stats refreshed after monitor deselection');
            })
            .catch(error => {
                console.error('Error refreshing dashboard stats:', error);
            });
    },
    
    // Close all SSE connections
    close: function() {
        console.log('Closing all SSE connections...');
        
        // Clear all reconnection timeouts
        if (this.reconnectTimeouts.dashboard) {
            clearTimeout(this.reconnectTimeouts.dashboard);
            this.reconnectTimeouts.dashboard = null;
        }
        if (this.reconnectTimeouts.monitor) {
            clearTimeout(this.reconnectTimeouts.monitor);
            this.reconnectTimeouts.monitor = null;
        }
        
        // Close dashboard stream
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.connectionState.dashboard = 'disconnected';
        
        // Close monitor stream
        if (this.monitorEventSource) {
            this.monitorEventSource.close();
            this.monitorEventSource = null;
        }
        this.connectionState.monitor = 'disconnected';
        
        // Reset reconnection attempts
        this.reconnectAttempts.dashboard = 0;
        this.reconnectAttempts.monitor = 0;
    },
    
    // Get connection status for debugging
    getConnectionStatus: function() {
        return {
            dashboard: this.connectionState.dashboard,
            monitor: this.connectionState.monitor,
            reconnectAttempts: {
                dashboard: this.reconnectAttempts.dashboard,
                monitor: this.reconnectAttempts.monitor
            }
        };
    },
    
    // Manually trigger reconnection (useful for debugging)
    reconnect: function() {
        console.log('Manual reconnection triggered...');
        this.close();
        setTimeout(() => {
            if (Uptimo.state.sseEnabled) {
                this.initialize();
            }
        }, 1000);
    }
};