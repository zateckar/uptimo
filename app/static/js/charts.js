// Uptimo JavaScript - Charts and Heartbeat Visualization
// This file contains chart management and heartbeat visualization

// Heartbeat visualization manager
const HeartbeatManager = {
    // Update detail view heartbeat
    updateDetailHeartbeat: function(checks) {
        const container = document.getElementById('heartbeatContainer');
        if (!container) return;
        
        // checks are already in row-based format from Utils.convertColumnarData()
        const heartbeatChecks = checks.slice(-50).reverse();
        
        if (heartbeatChecks.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No heartbeat data available</div>';
            return;
        }
        
        const html = heartbeatChecks.map(check => {
            const statusClass = check.s === 'up' ? 'beat-up' :
                              check.s === 'down' ? 'beat-down' : 'beat-unknown';
            
            // Build result-focused tooltip - using new minimal field format
            let tooltip = Utils.formatDateTime(check.t);  // t = timestamp
            
            // Show the actual result/error
            if (check.s === 'down' && check.e) {  // e = error_messages
                tooltip += `\n${check.e}`;
            } else if (check.c) {  // c = status_codes
                tooltip += `\nHTTP ${check.c}`;
            }
            
            // Add response time if available
            if (check.r) {  // r = response_times
                tooltip += `\n${Utils.formatResponseTime(check.r)}`;
            }
            
            return `<div class="beat beat-detail ${statusClass}" title="${tooltip}"></div>`;
        }).join('');
        
        container.innerHTML = `<div class="heartbeat-container">${html} <span class="text-xsmall text-muted"> now</span></div>`;
    },
    
    // Update sidebar heartbeat for single monitor
    updateSidebarHeartbeat: function(monitorId, checks) {
        const container = document.getElementById(`heartbeat-${monitorId}`);
        if (!container) return;
        
        // checks are already in row-based format from Utils.convertColumnarData()
        const heartbeatChecks = checks.slice(-25).reverse();
        
        if (heartbeatChecks.length === 0) {
            container.innerHTML = '<div class="text-muted">--</div>';
            return;
        }
        
        // For new monitors with fewer than 25 checks, always update since the array is growing
        // For established monitors, use heartbeatKey optimization
        let heartbeatKey = null;
        if (heartbeatChecks.length >= 25) {
            // Create a stable key for this heartbeat to prevent unnecessary DOM updates
            heartbeatKey = heartbeatChecks.map(check => `${check.s}-${check.t}`).join('|');
            
            // Check if we need to update (avoid DOM updates if data hasn't changed)
            if (container.dataset.heartbeatKey === heartbeatKey) {
                return;
            }
        }
        
        // Add timestamp to track last update time
        const latestTimestamp = heartbeatChecks.length > 0 ? heartbeatChecks[0].t : null;
        
        // For new monitors with growing arrays, always update regardless of timestamp
        // For established monitors, only update if new data is newer than existing data
        if (heartbeatChecks.length >= 25 && latestTimestamp && container.dataset.lastUpdate) {
            const existingTime = new Date(container.dataset.lastUpdate);
            const newTime = new Date(latestTimestamp);
            if (newTime <= existingTime) {
                return; // Don't update with older data for established monitors
            }
        }
        
        const html = heartbeatChecks.map(check => {
            const statusClass = check.s === 'up' ? 'beat-up' :
                              check.s === 'down' ? 'beat-down' : 'beat-unknown';
            
            // Build result-focused tooltip - using new minimal field format
            let tooltip = Utils.formatDateTime(check.t);  // t = timestamp
            
            // Show the actual result/error
            if (check.s === 'down' && check.e) {  // e = error_messages
                tooltip += `\n${check.e}`;
            } else if (check.c) {  // c = status_codes
                tooltip += `\nHTTP ${check.c}`;
            }
            
            // Add response time if available
            if (check.r) {  // r = response_times
                tooltip += `\n${Utils.formatResponseTime(check.r)}`;
            }
            
            // Smaller version for sidebar with reduced dimensions and margin
            return `<div class="beat beat-sidebar ${statusClass}" title="${tooltip}"></div>`;
        }).join('');
        
        container.innerHTML = `<div class="mini-heartbeat-container">${html}</div>`;
        
        // Only set heartbeatKey for established monitors (25+ checks)
        // For new monitors, we don't set this key to allow continuous updates
        if (heartbeatChecks.length >= 25) {
            container.dataset.heartbeatKey = heartbeatKey;
        } else {
            // Clear any existing heartbeatKey for new monitors to ensure updates
            delete container.dataset.heartbeatKey;
        }
        
        container.dataset.lastUpdate = latestTimestamp || new Date().toISOString();
    }
};

// Utility function to convert columnar data to objects
const ChartDataUtils = {
    convertColumnarToObjects: function(columnarData) {
        // Convert minimal columnar format back to objects for chart processing.
        // Expected input format: {t: [...], r: [...], s: [...], c: [...], e: [...]}
        // Output format: [{t: timestamp, r: response_time, s: status, c: status_code, e: error_message}, ...]
        if (!columnarData || !columnarData.t || columnarData.t.length === 0) {
            return [];
        }
        
        const objects = [];
        for (let i = 0; i < columnarData.t.length; i++) {
            objects.push({
                t: columnarData.t[i],  // timestamp
                r: columnarData.r[i],  // response_time
                s: columnarData.s[i],  // status
                c: columnarData.c[i],  // status_code
                e: columnarData.e[i]   // error_message
            });
        }
        
        return objects;
    }
};

// Chart management
const ChartManager = {
    // Store last known data to prevent unnecessary updates
    lastChartData: {
        checks: null,
        timespan: null,
        dataHash: null
    },

    // Update response time chart
    updateResponseTimeChart: function(checks, timespan = '24h') {
        const canvas = document.getElementById('responseTimeChart');
        if (!canvas) {
            return;
        }
        
        // checks are already in row-based format from Utils.convertColumnarData()
        const currentDataHash = this.createDataHash(checks, timespan);
        
        // Skip update if data hasn't meaningfully changed
        if (this.lastChartData.dataHash === currentDataHash &&
            this.lastChartData.timespan === timespan) {
            return;
        }
        
        // Get context
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (Uptimo.state.charts.responseTime) {
            Uptimo.state.charts.responseTime.destroy();
            Uptimo.state.charts.responseTime = null;
        }
        
        // Clear any existing chart instances on this canvas
        Chart.getChart(canvas)?.destroy();
        
        // Filter by timespan (reusing the already converted checks)
        const filteredChecks = this.filterChecksByTimespan(checks, timespan);
        
        // Create properly spaced data for linear timescale
        // We pass all filtered checks to createLinearTimescaleData which will handle
        // downsampling by bucketing data into time intervals
        // Get monitor interval for adaptive bucketing
        const monitorInterval = this.getMonitorInterval();
        const chartData = this.createLinearTimescaleData(filteredChecks, timespan, monitorInterval);
        
        const labels = chartData.labels;
        const data = chartData.values;
        const statuses = chartData.statuses;
        
        // CRITICAL FIX: Use the direct tooltip check data for precise tooltip lookup
        // This ensures tooltips show the correct data, especially for high-frequency monitors (30s intervals)
        const tooltipChecks = chartData.tooltipChecks || [];
        
        // Create color arrays based on status
        const pointColors = statuses.map(status => {
            if (status === 'up') return '#198754';  // green
            if (status === 'down') return '#dc3545';  // red
            return '#6c757d';  // gray for unknown/null
        });
        
        const pointBorderColors = pointColors;
        
        // Create new chart with error handling
        try {
            Uptimo.state.charts.responseTime = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Response Time',
                        data: data,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        spanGaps: true,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: pointBorderColors,
                        pointBorderWidth: 2,
                        segment: {
                            borderColor: (ctx) => {
                                // Color line segments based on the status of the point
                                const index = ctx.p0DataIndex;
                                if (statuses[index] === 'up') return '#198754';
                                if (statuses[index] === 'down') return '#dc3545';
                                return '#6c757d';
                            },
                            backgroundColor: (ctx) => {
                                const index = ctx.p0DataIndex;
                                if (statuses[index] === 'up') return 'rgba(25, 135, 84, 0.1)';
                                if (statuses[index] === 'down') return 'rgba(220, 53, 69, 0.1)';
                                return 'rgba(108, 117, 125, 0.1)';
                            }
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) {
                                    const index = context[0].dataIndex;
                                    const label = labels[index];
                                    
                                    // Debug logging to help identify the issue
                                    if (console.debug && Uptimo.config.debug) {
                                        console.debug('Chart tooltip - label:', label, 'index:', index);
                                        console.debug('Chart tooltip - sortedChecks length:', sortedChecksForTooltip ? sortedChecksForTooltip.length : 'undefined');
                                        if (sortedChecksForTooltip && sortedChecksForTooltip.length > 0) {
                                            console.debug('Chart tooltip - first sorted check:', sortedChecksForTooltip[0]);
                                        }
                                    }
                                    
                                    // CRITICAL FIX: Use direct tooltip check data instead of timestamp matching
                                    // This ensures tooltips show the correct data, especially for high-frequency monitors (30s intervals)
                                    let check = null;
                                    
                                    // Use the precise tooltip check data if available
                                    if (tooltipChecks.length > 0 && index < tooltipChecks.length) {
                                        check = tooltipChecks[index];
                                    }
                                    
                                    // Fallback: try to find check by timestamp if direct lookup failed
                                    if (!check && typeof label === 'string') {
                                        const labelTime = new Date(label).getTime();
                                        if (!isNaN(labelTime)) {
                                            check = sortedChecksForTooltip.find(c => {
                                                const checkTime = new Date(c.t).getTime();
                                                // Allow a small time window for matching (within 1 minute)
                                                return Math.abs(checkTime - labelTime) < 60000;
                                            });
                                        }
                                    }
                                    
                                    // Use the original timestamp from the check if found, otherwise use the label
                                    if (check && check.t) {
                                        // Ensure APP_TIMEZONE is available before formatting
                                        if (!window.APP_TIMEZONE && window.Uptimo && window.Uptimo.config && window.Uptimo.config.timezone) {
                                            window.APP_TIMEZONE = window.Uptimo.config.timezone;
                                        }
                                        const formatted = Utils.formatDateTime(check.t);
                                        // If formatting still returns "Invalid Data", use a fallback with timezone
                                        if (formatted === 'Invalid Data') {
                                            const timezone = window.APP_TIMEZONE || 'UTC';
                                            return new Date(check.t).toLocaleString('en-US', {
                                                timeZone: timezone,
                                                year: 'numeric',
                                                month: '2-digit',
                                                day: '2-digit',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                second: '2-digit',
                                                hour12: false
                                            });
                                        }
                                        return formatted;
                                    } else {
                                        // Ensure APP_TIMEZONE is available before formatting
                                        if (!window.APP_TIMEZONE && window.Uptimo && window.Uptimo.config && window.Uptimo.config.timezone) {
                                            window.APP_TIMEZONE = window.Uptimo.config.timezone;
                                        }
                                        const formatted = Utils.formatDateTime(label);
                                        // If formatting still returns "Invalid Data", use a fallback with timezone
                                        if (formatted === 'Invalid Data') {
                                            const timezone = window.APP_TIMEZONE || 'UTC';
                                            return new Date(label).toLocaleString('en-US', {
                                                timeZone: timezone,
                                                year: 'numeric',
                                                month: '2-digit',
                                                day: '2-digit',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                second: '2-digit',
                                                hour12: false
                                            });
                                        }
                                        return formatted;
                                    }
                                },
                                label: function(context) {
                                    const index = context.dataIndex;
                                    const value = context.parsed.y;
                                    const status = statuses[index];
                                    
                                    let lines = [];
                                    
                                    // Add status
                                    if (status === 'up') {
                                        lines.push('Status: ✅ Up');
                                    } else if (status === 'down') {
                                        lines.push('Status: ❌ Down');
                                    } else {
                                        lines.push('Status: ❓ Unknown');
                                    }
                                    
                                    // Add response time
                                    if (value && value > 0) {
                                        lines.push(`Response Time: ${Utils.formatResponseTime(value)}`);
                                    } else {
                                        lines.push('Response Time: Timeout');
                                    }
                                    
                                    return lines;
                                },
                                afterLabel: function(context) {
                                    const index = context.dataIndex;
                                    const status = statuses[index];
                                    
                                    // Get the raw check data for this point
                                    const chartData = context.chart.data;
                                    const label = chartData.labels[index];
                                    
                                    // CRITICAL FIX: Use direct tooltip check data instead of timestamp matching
                                    // This ensures tooltips show the correct data, especially for high-frequency monitors (30s intervals)
                                    let check = null;
                                    
                                    // Use the precise tooltip check data if available
                                    if (tooltipChecks.length > 0 && index < tooltipChecks.length) {
                                        check = tooltipChecks[index];
                                    }
                                    
                                    // Fallback: try to find check by timestamp if direct lookup failed
                                    if (!check && typeof label === 'string' && label.includes('T') && label.includes('Z')) {
                                        const labelTime = new Date(label).getTime();
                                        if (!isNaN(labelTime)) {
                                            check = sortedChecksForTooltip.find(c => {
                                                const checkTime = new Date(c.t).getTime();
                                                // Allow a small time window for matching (within 1 minute)
                                                return Math.abs(checkTime - labelTime) < 60000;
                                            });
                                        }
                                    }
                                    
                                    if (check) {
                                        let lines = [];
                                        
                                        // Show error message for failed checks
                                        if (status === 'down' && check.e) {
                                            lines.push(`Error: ${check.e}`);
                                        }
                                        
                                        // Show HTTP status code if available
                                        if (check.c) {
                                            lines.push(`HTTP Status: ${check.c}`);
                                        }
                                        
                                        return lines.length > 0 ? lines : null;
                                    }
                                    
                                    return null;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: this.getTimespanLabel(timespan)
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: "Response Time"
                            },
                            ticks: {
                                callback: function(value) {
                                    return Utils.formatResponseTime(value);
                                }
                            }
                        }
                    },
                    interaction: {
                        mode: "nearest",
                        axis: "x",
                        intersect: false
                    }
                }
            });
            
            // Store the current data hash to prevent unnecessary updates
            this.lastChartData = {
                checks: checks.slice(), // Store a copy
                timespan: timespan,
                dataHash: currentDataHash
            };
            
        } catch (error) {
            console.error("Error creating response time chart:", error);
            Utils.showToast("Failed to create response time chart", "danger");
        }
    },

    // Create a hash of the meaningful chart data to detect changes
    createDataHash: function(checks, timespan) {
        if (!checks || checks.length === 0) {
            return `empty-${timespan}`;
        }
        
        // Sort checks by timestamp (newest first) for consistent hashing
        // This ensures we're always comparing the most recent data
        const sortedForHash = [...checks].sort((a, b) =>
            new Date(b.t) - new Date(a.t)  // b.t - a.t = descending (newest first)
        );
        
        // Only hash the meaningful parts: timestamp, status, response_time
        // Look at the first 50 items (the most recent ones)
        const meaningfulData = sortedForHash.slice(0, 50).map(check => ({
            t: check.t,  // timestamp
            s: check.s,  // status
            r: check.r   // response_time
        }));
        
        // Simple string hash function
        const str = JSON.stringify({
            timespan: timespan,
            count: meaningfulData.length,
            data: meaningfulData
        });
        
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        
        return hash.toString();
    },
    
    // Filter checks by timespan
    filterChecksByTimespan: function(checks, timespan) {
        if (!checks || checks.length === 0) return [];
        
        const now = new Date();
        let cutoffTime;
        
        switch (timespan) {
            case "1h":
                cutoffTime = new Date(now.getTime() - 60 * 60 * 1000);
                break;
            case "6h":
                cutoffTime = new Date(now.getTime() - 6 * 60 * 60 * 1000);
                break;
            case "24h":
                cutoffTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
            case "7d":
                cutoffTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case "30d":
                cutoffTime = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                break;
            default:
                cutoffTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        }
        
        // Filter by timespan and then sort by timestamp (oldest first)
        const filtered = checks.filter(check => new Date(check.t) >= cutoffTime);
        const sorted = filtered.sort((a, b) => new Date(a.t) - new Date(b.t));
        
        // Debug: Log filtering results
        if (console.debug && Uptimo.config.debug) {
            console.debug('filterChecksByTimespan results:');
            console.debug('- Input checks count:', checks.length);
            console.debug('- First input check:', checks[0]?.t);
            console.debug('- Last input check:', checks[checks.length - 1]?.t);
            console.debug('- Filtered count:', filtered.length);
            console.debug('- First filtered check:', filtered[0]?.t);
            console.debug('- Last filtered check:', filtered[filtered.length - 1]?.t);
            console.debug('- First sorted check:', sorted[0]?.t);
            console.debug('- Last sorted check:', sorted[sorted.length - 1]?.t);
        }
        
        return sorted;
    },
    
    // Get maximum data points for timespan
    getMaxDataPointsForTimespan: function(timespan) {
        switch (timespan) {
            case "1h": return 60;
            case "6h": return 72;
            case "24h": return 96;
            case "7d": return 168;
            case "30d": return 180;
            default: return 100;
        }
    },
    
    // Format label for timespan
    formatLabelForTimespan: function(timestamp, timespan) {
        const date = new Date(timestamp);
        // Ensure APP_TIMEZONE is available with multiple fallbacks
        let timezone = window.APP_TIMEZONE;
        if (!timezone) {
            // Try to get timezone from Uptimo config
            if (window.Uptimo && window.Uptimo.config && window.Uptimo.config.timezone) {
                timezone = window.Uptimo.config.timezone;
                window.APP_TIMEZONE = timezone; // Set it for future use
            } else {
                timezone = 'UTC';
            }
        }
        
        try {
            switch (timespan) {
                case "1h":
                    // Show time only for 1h view
                    return date.toLocaleTimeString('en-US', {
                        timeZone: timezone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "6h":
                    // Show time with hour markers for 6h view
                    return date.toLocaleTimeString('en-US', {
                        timeZone: timezone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "24h":
                    // Show time + date for 24h view
                    return date.toLocaleString('en-US', {
                        timeZone: timezone,
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "7d":
                    // Show date + time for 7d view
                    return date.toLocaleDateString('en-US', {
                        timeZone: timezone,
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        hour12: false
                    });
                case "30d":
                    // Show date only for 30d view
                    return date.toLocaleDateString('en-US', {
                        timeZone: timezone,
                        month: "short",
                        day: "numeric"
                    });
                default:
                    return date.toLocaleString('en-US', {
                        timeZone: timezone,
                        hour12: false
                    });
            }
        } catch (e) {
            // Fallback to UTC if timezone is invalid
            console.warn(`Invalid timezone '${timezone}', using UTC for chart labels`);
            return date.toLocaleString('en-US', {
                timeZone: 'UTC',
                hour12: false
            });
        }
    },
    
    // Get timespan label
    getTimespanLabel: function(timespan) {
        switch (timespan) {
            case "1h": return "Last Hour";
            case "6h": return "Last 6 Hours";
            case "24h": return "Last 24 Hours";
            case "7d": return "Last 7 Days";
            case "30d": return "Last 30 Days";
            default: return "Time";
        }
    },
    
    // Get monitor check interval from DOM or cache
    getMonitorInterval: function() {
        // Try to get from selected monitor element (by ID)
        if (Uptimo.state.selectedMonitorId) {
            const selectedMonitor = document.querySelector(`[data-monitor-id="${Uptimo.state.selectedMonitorId}"]`);
            if (selectedMonitor) {
                const interval = selectedMonitor.dataset.checkInterval;
                if (interval) {
                    // Handle enum strings like "CheckInterval.THIRTY_SECONDS"
                    let intervalSeconds;
                    if (typeof interval === 'string' && interval.includes('THIRTY_SECONDS')) {
                        intervalSeconds = 30;
                    } else if (typeof interval === 'string' && interval.includes('ONE_MINUTE')) {
                        intervalSeconds = 60;
                    } else if (typeof interval === 'string' && interval.includes('FIVE_MINUTES')) {
                        intervalSeconds = 300;
                    } else {
                        // Try to parse as number
                        intervalSeconds = parseInt(interval);
                    }
                    
                    const intervalMs = intervalSeconds * 1000;
                    if (!isNaN(intervalMs) && intervalMs > 0) {
                        return intervalMs;
                    }
                }
            }
        }
        
        // Try to get from global state
        if (Uptimo.state.selectedMonitorId && Uptimo.state.monitorData) {
            const monitor = Uptimo.state.monitorData[Uptimo.state.selectedMonitorId];
            if (monitor && monitor.check_interval) {
                const intervalMs = monitor.check_interval * 1000;
                if (!isNaN(intervalMs)) {
                    return intervalMs;
                }
            }
        }
        
        // Default to 5 minutes (300 seconds)
        return 5 * 60 * 1000;
    },
    
    // Get optimal time interval based on monitor frequency and timespan
    getOptimalTimeInterval: function(monitorIntervalMs, timespan) {
        const timespanHours = {
            '1h': 1,
            '6h': 6,
            '24h': 24,
            '7d': 168,
            '30d': 720
        }[timespan];
        
        // For shorter timespans, use smaller intervals to show more detail
        let maxDataPoints;
        if (timespanHours <= 1) {
            maxDataPoints = 60;  // 1-minute intervals for 1h
        } else if (timespanHours <= 6) {
            maxDataPoints = 72;  // 5-minute intervals for 6h
        } else if (timespanHours <= 24) {
            maxDataPoints = 96;  // 15-minute intervals for 24h
        } else if (timespanHours <= 168) {
            maxDataPoints = 168; // 1-hour intervals for 7d
        } else {
            maxDataPoints = 180; // 4-hour intervals for 30d
        }
        
        const timespanMs = timespanHours * 60 * 60 * 1000;
        const optimalIntervalMs = Math.ceil(timespanMs / maxDataPoints);
        
        // Ensure we don't use intervals smaller than the monitor check interval
        const finalIntervalMs = Math.max(optimalIntervalMs, monitorIntervalMs);
        
        return finalIntervalMs;
    },
    
    // Create time buckets for the given timespan
    createTimeBuckets: function(startTime, endTime, timeIntervalMs) {
        const buckets = [];
        const bucketCount = Math.ceil((endTime.getTime() - startTime.getTime()) / timeIntervalMs);
        
        // Limit bucket count to reasonable maximum
        const maxBuckets = 100;
        const actualIntervalMs = Math.max(timeIntervalMs, (endTime.getTime() - startTime.getTime()) / maxBuckets);
        
        for (let time = startTime.getTime(); time < endTime.getTime(); time += actualIntervalMs) {
            buckets.push({
                start: new Date(time),
                end: new Date(Math.min(time + actualIntervalMs, endTime.getTime())),
                assignedCheck: null
            });
        }
        
        return buckets;
    },
    
    // Aggregate checks into buckets for consistent visualization
    assignChecksToBuckets: function(sortedChecks, buckets) {
        let checkIndex = 0;
        
        for (let bucketIndex = 0; bucketIndex < buckets.length && checkIndex < sortedChecks.length; bucketIndex++) {
            const bucket = buckets[bucketIndex];
            const bucketChecks = [];
            
            // Collect all checks that belong to this bucket
            for (let i = checkIndex; i < sortedChecks.length; i++) {
                const check = sortedChecks[i];
                const checkTime = new Date(check.t);
                
                // Skip checks before this bucket
                if (checkTime < bucket.start) continue;
                
                // Skip checks after this bucket - we'll use them for next buckets
                if (checkTime >= bucket.end) break;
                
                bucketChecks.push(check);
            }
            
            // Aggregate the checks for this bucket
            if (bucketChecks.length > 0) {
                bucket.assignedCheck = this.aggregateBucketChecks(bucketChecks);
                // Move check index past all checks used for this bucket
                checkIndex += bucketChecks.length;
            }
        }
    },
    
    // Aggregate multiple checks into a single representative check
    aggregateBucketChecks: function(checks) {
        // Separate checks by status
        const upChecks = checks.filter(c => c.s === 'up' && c.r !== null);
        const downChecks = checks.filter(c => c.s === 'down');
        const timeoutChecks = downChecks.filter(c => c.r === null);
        
        // Determine the dominant status (prioritize timeouts and downs)
        let dominantStatus;
        if (timeoutChecks.length > 0) {
            dominantStatus = 'down'; // Timeout takes priority
        } else if (downChecks.length > 0) {
            dominantStatus = 'down';
        } else if (upChecks.length > 0) {
            dominantStatus = 'up';
        } else {
            dominantStatus = 'unknown';
        }
        
        // Calculate response time based on status
        let responseTime;
        if (dominantStatus === 'down') {
            // For downs, check if there are timeouts
            if (timeoutChecks.length > 0) {
                responseTime = 0; // Timeout represented as 0
            } else {
                // For non-timeout downs, use average of any available response times
                const downWithTime = downChecks.filter(c => c.r !== null);
                if (downWithTime.length > 0) {
                    const sum = downWithTime.reduce((acc, c) => acc + c.r, 0);
                    responseTime = sum / downWithTime.length;
                } else {
                    responseTime = 0; // No response times available
                }
            }
        } else if (dominantStatus === 'up' && upChecks.length > 0) {
            // For ups, use median for better representation of typical values
            const times = upChecks.map(c => c.r).sort((a, b) => a - b);
            const mid = Math.floor(times.length / 2);
            responseTime = times.length % 2 === 0
                ? (times[mid - 1] + times[mid]) / 2  // Even: average of middle two
                : times[mid];  // Odd: middle value
        } else {
            responseTime = null;
        }
        
        // Use the timestamp of the middle check for temporal representation
        const middleIndex = Math.floor(checks.length / 2);
        const representativeCheck = {
            ...checks[middleIndex],
            status: dominantStatus,
            response_time: responseTime
        };
        
        return representativeCheck;
    },
    
    // Convert buckets to chart data format
    bucketsToChartData: function(buckets, timespan) {
        const labels = [];
        const values = [];
        const statuses = [];
        const tooltipChecks = []; // Store the actual check data for tooltip lookup
        
        buckets.forEach(bucket => {
            if (bucket.assignedCheck) {
                // CRITICAL FIX: Use the actual assigned check timestamp for the label
                // This ensures tooltip matching works correctly, especially for high-frequency monitors (30s intervals)
                labels.push(this.formatLabelForTimespan(
                    bucket.assignedCheck.t, // Use assigned check timestamp, not bucket start
                    timespan
                ));
                
                // For timeout checks with null response_time, use 0 to ensure they appear in chart
                // The status will still be "down" so it will be colored red
                const responseTime = bucket.assignedCheck.response_time !== null
                    ? bucket.assignedCheck.response_time
                    : 0;
                values.push(responseTime);
                statuses.push(bucket.assignedCheck.status);
                
                // Store the actual check data for direct tooltip lookup
                tooltipChecks.push(bucket.assignedCheck);
            } else {
                // For empty buckets, use bucket start time for label (no tooltip data needed)
                labels.push(this.formatLabelForTimespan(
                    bucket.start.toISOString(),
                    timespan
                ));
                values.push(null);
                statuses.push(null);
                tooltipChecks.push(null);
            }
        });
        
        // Debug: Log the bucket order before any reversal
        if (console.debug && Uptimo.config.debug) {
            console.debug('Bucket data before potential reversal:');
            console.debug('First label:', labels[0]);
            console.debug('Last label:', labels[labels.length - 1]);
            console.debug('First tooltip check timestamp:', tooltipChecks[0]?.t);
            console.debug('Last tooltip check timestamp:', tooltipChecks[tooltipChecks.length - 1]?.t);
        }
        
        return { labels, values, statuses, tooltipChecks };
    },
    
    // Create linear timescale data with adaptive bucketing (FIXED VERSION)
    createLinearTimescaleData: function(checks, timespan, monitorIntervalMs = 5 * 60 * 1000) {
        if (!checks || checks.length === 0) {
            return { labels: [], values: [], statuses: [] };
        }
        
        const now = new Date();
        const timespanHours = {
            '1h': 1,
            '6h': 6,
            '24h': 24,
            '7d': 168,
            '30d': 720
        }[timespan];
        
        // Create fixed time boundaries that don't shift with each update
        const { startTime, endTime } = this.createFixedTimeBoundaries(now, timespanHours);
        const timeIntervalMs = this.getOptimalTimeInterval(monitorIntervalMs, timespan);
        
        // Debug: Log the original data order
        if (console.debug && Uptimo.config.debug) {
            console.debug('Original checks order (first 3):', checks.slice(0, 3).map(c => ({ t: c.t, r: c.r })));
        }
        
        // CRITICAL FIX: Explicitly sort checks in chronological order (oldest to newest)
        // This ensures the chart displays left-to-right (past to present) correctly
        // Even though filterChecksByTimespan should sort, we guarantee it here
        const sortedChecks = [...checks].sort((a, b) =>
            new Date(a.t).getTime() - new Date(b.t).getTime()  // Ascending: oldest first
        );
        
        // Debug: Log the sorted data order
        if (console.debug && Uptimo.config.debug) {
            console.debug('Sorted checks order (first 3):', sortedChecks.slice(0, 3).map(c => ({ t: c.t, r: c.r })));
            console.debug('Time boundaries:', { startTime: startTime.toISOString(), endTime: endTime.toISOString() });
        }
        
        // Create time buckets with fixed boundaries
        const buckets = this.createTimeBuckets(startTime, endTime, timeIntervalMs);
        
        // Debug: Log bucket creation
        if (console.debug && Uptimo.config.debug) {
            console.debug('Created buckets:', buckets.length);
            console.debug('First bucket start:', buckets[0]?.start.toISOString());
            console.debug('Last bucket start:', buckets[buckets.length - 1]?.start.toISOString());
        }
        
        // Assign checks to buckets - one check per bucket maximum
        this.assignChecksToBuckets(sortedChecks, buckets);
        
        // Convert buckets to chart data
        const result = this.bucketsToChartData(buckets, timespan);
        
        // Debug: Log final result
        if (console.debug && Uptimo.config.debug) {
            console.debug('Final chart result labels (first 3):', result.labels.slice(0, 3));
            console.debug('Final chart result labels (last 3):', result.labels.slice(-3));
        }
        
        // Fallback: if no data was assigned, use simple direct mapping
        // This is a safety net for edge cases where bucket assignment fails
        if (result.values.filter(v => v !== null).length === 0 && sortedChecks.length > 0) {
            console.warn('Bucket assignment failed, using fallback direct mapping for chart data');
            return this.createSimpleChartData(sortedChecks, timespan);
        }
        
        // Include the sorted checks in the result for tooltip lookup
        result.sortedChecks = sortedChecks;
        
        return result;
    },
    
    // Create fixed time boundaries that align to regular intervals
    createFixedTimeBoundaries: function(now, timespanHours) {
        const timespanMs = timespanHours * 60 * 60 * 1000;
        
        // For different timespans, align to different boundary intervals
        let alignmentIntervalMs;
        if (timespanHours <= 1) {
            // For 1h, align to minute boundaries
            alignmentIntervalMs = 60 * 1000;
        } else if (timespanHours <= 6) {
            // For 6h, align to 5-minute boundaries
            alignmentIntervalMs = 5 * 60 * 1000;
        } else if (timespanHours <= 24) {
            // For 24h, align to 15-minute boundaries
            alignmentIntervalMs = 15 * 60 * 1000;
        } else if (timespanHours <= 168) {
            // For 7d, align to hour boundaries
            alignmentIntervalMs = 60 * 60 * 1000;
        } else {
            // For 30d, align to 4-hour boundaries
            alignmentIntervalMs = 4 * 60 * 60 * 1000;
        }
        
        // Calculate the end time aligned to the boundary (this should be "now" or slightly after)
        const endTime = new Date(Math.ceil(now.getTime() / alignmentIntervalMs) * alignmentIntervalMs);
        // Calculate start time as end time minus the timespan duration
        const startTime = new Date(endTime.getTime() - timespanMs);
        
        // Debug: Log the time boundaries
        if (console.debug && Uptimo.config.debug) {
            console.debug('Time boundaries created:', {
                now: now.toISOString(),
                timespanHours: timespanHours,
                timespanMs: timespanMs,
                startTime: startTime.toISOString(),
                endTime: endTime.toISOString(),
                durationHours: (endTime.getTime() - startTime.getTime()) / (60 * 60 * 1000)
            });
        }
        
        return { startTime, endTime };
    },
    
    // Simple fallback: direct mapping of checks to chart data
    createSimpleChartData: function(checks, timespan) {
        
        const maxDataPoints = this.getMaxDataPointsForTimespan(timespan);
        
        // Sort checks by timestamp (oldest first) for proper left-to-right timeline
        const sortedChecks = [...checks].sort((a, b) =>
            new Date(a.t) - new Date(b.t)  // t = timestamp
        );
        
        // If we have too many checks, sample them evenly
        let sampledChecks = sortedChecks;
        if (sortedChecks.length > maxDataPoints) {
            const step = Math.ceil(sortedChecks.length / maxDataPoints);
            sampledChecks = sortedChecks.filter((_, index) => index % step === 0);
        }
        
        const labels = [];
        const values = [];
        const statuses = [];
        
        sampledChecks.forEach(check => {
            labels.push(this.formatLabelForTimespan(check.t, timespan));
            // For timeout checks with null response_time, use 0 to ensure they appear in chart
            const responseTime = check.r !== null ? check.r : 0;
            values.push(responseTime);
            statuses.push(check.s);
        });
        
        return { labels, values, statuses };
    }
};