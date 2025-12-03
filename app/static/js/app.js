// Uptimo JavaScript - Application Initialization
// This file initializes the application and coordinates all modules

// Initialize heartbeats for server-rendered monitor list
function initializeServerRenderedHeartbeats() {
    // Don't load heartbeat data separately since SSE will provide it
    // This prevents fake data from overriding real SSE data
    console.log('Heartbeat initialization deferred to SSE streams');
}

// Setup event listeners
function setupEventListeners() {
    // Timespan buttons
    document.querySelectorAll(".timespan-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            TimespanManager.changeTimespan(this.dataset.timespan);
        });
    });
    
    // Monitor click handlers
    document.querySelectorAll(".monitor-item[data-monitor-id]").forEach(item => {
        item.addEventListener("click", function() {
            const monitorId = parseInt(this.dataset.monitorId);
            MonitorManager.loadDetails(monitorId);
        });
    });
}

// Handle page visibility changes to manage SSE connections
function setupPageVisibilityHandler() {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log('Page became hidden, keeping SSE connections active');
            // We keep SSE connections active even when page is hidden
            // This ensures we don't miss any updates when user returns
        } else {
            console.log('Page became visible, checking SSE connection status');
            // Check if SSE connections are still active when page becomes visible
            const status = SSEManager.getConnectionStatus();
            console.log('SSE Connection Status:', status);
            
            // If both connections are failed, attempt reconnection
            if (status.dashboard === 'failed' && status.monitor === 'failed') {
                console.log('Both SSE connections failed, attempting reconnection...');
                SSEManager.reconnect();
            }
        }
    });
    
    // Handle page unload to properly close connections
    window.addEventListener('beforeunload', function() {
        console.log('Page unloading, closing SSE connections...');
        SSEManager.close();
    });
    
    // Handle online/offline events
    window.addEventListener('online', function() {
        console.log('Network connection restored');
        Utils.showToast('Network connection restored', 'success');
        // Attempt to reconnect SSE when network is restored
        SSEManager.reconnect();
    });
    
    window.addEventListener('offline', function() {
        console.log('Network connection lost');
        Utils.showToast('Network connection lost', 'warning');
        // SSE will automatically handle reconnection when network returns
    });
}

// Auto-select monitor on page load
function autoSelectMonitor() {
    // Try to get last selected monitor from cookie
    const lastSelectedId = MonitorSelectionManager.getLastSelectedMonitor();
    
    // Check if we have any monitors
    const monitorItems = document.querySelectorAll('.monitor-item[data-monitor-id]');
    
    if (monitorItems.length === 0) {
        // No monitors available
        return;
    }
    
    let monitorToSelect = null;
    
    // If we have a last selected monitor, try to find it
    if (lastSelectedId) {
        const lastMonitor = document.querySelector(
            `.monitor-item[data-monitor-id="${lastSelectedId}"]`
        );
        if (lastMonitor) {
            monitorToSelect = lastMonitor;
            console.log(`Auto-selecting last viewed monitor: ${lastSelectedId}`);
        }
    }
    
    // If no last selected monitor or it doesn't exist, select the first one
    if (!monitorToSelect) {
        monitorToSelect = monitorItems[0];
        const firstMonitorId = monitorToSelect.dataset.monitorId;
        console.log(`Auto-selecting first monitor: ${firstMonitorId}`);
    }
    
    // Trigger selection
    if (monitorToSelect) {
        const monitorId = parseInt(monitorToSelect.dataset.monitorId);
        MonitorManager.loadDetails(monitorId);
    }
}

// Initialize application
document.addEventListener("DOMContentLoaded", function() {
    console.log("🚀 Uptimo Dashboard Initializing...");
    console.log("📊 Auto-refresh:", Uptimo.state.autoRefreshEnabled ? "ENABLED" : "DISABLED");
    console.log("🔌 SSE:", Uptimo.state.sseEnabled ? "ENABLED" : "DISABLED");
    
    // Note: Theme is initialized in utils.js for all users
    
    // Initialize SSE for real-time updates (auto-refresh is disabled)
    SSEManager.initialize();
    
    // Initialize heartbeats for server-rendered monitors
    initializeServerRenderedHeartbeats();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up page visibility handler to manage SSE connections
    setupPageVisibilityHandler();
    
    // Auto-select monitor (last viewed or first available)
    autoSelectMonitor();
    
    // Expose managers to window for debugging
    window.SSEManager = SSEManager;
    window.ThemeManager = ThemeManager;
    window.MonitorSelectionManager = MonitorSelectionManager;
});

// Export global functions for inline event handlers
window.MonitorManager = MonitorManager;
window.TimespanManager = TimespanManager;