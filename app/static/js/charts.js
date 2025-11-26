// Uptimo JavaScript - Charts and Heartbeat Visualization
// This file contains chart management and heartbeat visualization

// Heartbeat visualization manager
const HeartbeatManager = {
    // Update detail view heartbeat
    updateDetailHeartbeat: function(checks) {
        const container = document.getElementById('heartbeatContainer');
        if (!container) return;
        
        // Get last 50 checks for heartbeat visualization
        const heartbeatChecks = checks.slice(-50).reverse();
        
        if (heartbeatChecks.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No heartbeat data available</div>';
            return;
        }
        
        const html = heartbeatChecks.map(check => {
            const statusClass = check.status === 'up' ? 'beat-up' :
                              check.status === 'down' ? 'beat-down' : 'beat-unknown';
            
            // Build result-focused tooltip
            let tooltip = Utils.formatDateTime(check.timestamp);
            
            // Show the actual result/error
            if (check.status === 'down' && check.error_message) {
                tooltip += `\n${check.error_message}`;
            } else if (check.status_code) {
                tooltip += `\nHTTP ${check.status_code}`;
            }
            
            // Add response time if available
            if (check.response_time) {
                tooltip += `\n${Utils.formatResponseTime(check.response_time)}`;
            }
            
            return `<div class="beat beat-detail ${statusClass}" title="${tooltip}"></div>`;
        }).join('');
        
        container.innerHTML = `<div class="heartbeat-container">${html}</div>`;
    },
    
    // Update sidebar heartbeat for single monitor
    updateSidebarHeartbeat: function(monitorId, checks) {
        const container = document.getElementById(`heartbeat-${monitorId}`);
        if (!container) return;
        
        // Get last 25 checks for mini heartbeat
        const heartbeatChecks = checks.slice(-25).reverse();
        
        if (heartbeatChecks.length === 0) {
            container.innerHTML = '<div class="text-muted">--</div>';
            return;
        }
        
        // Create a stable key for this heartbeat to prevent unnecessary DOM updates
        const heartbeatKey = heartbeatChecks.map(check => `${check.status}-${check.timestamp}`).join('|');
        
        // Check if we need to update (avoid DOM updates if data hasn't changed)
        if (container.dataset.heartbeatKey === heartbeatKey) {
            return;
        }
        
        // Add timestamp to track last update time
        const latestTimestamp = heartbeatChecks.length > 0 ? heartbeatChecks[0].timestamp : null;
        
        // Only update if new data is newer than existing data
        if (latestTimestamp && container.dataset.lastUpdate) {
            const existingTime = new Date(container.dataset.lastUpdate);
            const newTime = new Date(latestTimestamp);
            if (newTime <= existingTime) {
                return; // Don't update with older data
            }
        }
        
        const html = heartbeatChecks.map(check => {
            const statusClass = check.status === 'up' ? 'beat-up' :
                              check.status === 'down' ? 'beat-down' : 'beat-unknown';
            
            // Build result-focused tooltip
            let tooltip = Utils.formatDateTime(check.timestamp);
            
            // Show the actual result/error
            if (check.status === 'down' && check.error_message) {
                tooltip += `\n${check.error_message}`;
            } else if (check.status_code) {
                tooltip += `\nHTTP ${check.status_code}`;
            }
            
            // Add response time if available
            if (check.response_time) {
                tooltip += `\n${Utils.formatResponseTime(check.response_time)}`;
            }
            
            // Smaller version for sidebar with reduced dimensions and margin
            return `<div class="beat beat-sidebar ${statusClass}" title="${tooltip}"></div>`;
        }).join('');
        
        container.innerHTML = `<div class="mini-heartbeat-container">${html}</div>`;
        container.dataset.heartbeatKey = heartbeatKey;
        container.dataset.lastUpdate = latestTimestamp || new Date().toISOString();
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
            console.warn('Response time chart canvas not found');
            return;
        }
        
        // Create a hash of the meaningful data to detect actual changes
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
        
        // Filter data based on timespan
        const filteredChecks = this.filterChecksByTimespan(checks, timespan);
        
        // Create properly spaced data for linear timescale
        // We pass all filtered checks to createLinearTimescaleData which will handle
        // downsampling by bucketing data into time intervals
        const chartData = this.createLinearTimescaleData(filteredChecks, timespan);
        
        const labels = chartData.labels;
        const data = chartData.values;
        const statuses = chartData.statuses;
        
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
                                label: function(context) {
                                    const value = context.parsed.y;
                                    return value ? `Response Time: ${Utils.formatResponseTime(value)}` : 'No data';
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
        
        // Only hash the meaningful parts: timestamp, status, response_time
        // Since checks are sorted by timestamp descending (newest first),
        // we should look at the first 50 items (the most recent ones)
        const meaningfulData = checks.slice(0, 50).map(check => ({
            t: check.timestamp,
            s: check.status,
            r: check.response_time
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
        
        return checks.filter(check => new Date(check.timestamp) >= cutoffTime);
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
        const timezone = window.APP_TIMEZONE || 'UTC';
        
        try {
            switch (timespan) {
                case "1h":
                    return date.toLocaleTimeString('en-US', {
                        timeZone: timezone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "6h":
                    return date.toLocaleTimeString('en-US', {
                        timeZone: timezone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "24h":
                    return date.toLocaleTimeString('en-US', {
                        timeZone: timezone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    });
                case "7d":
                    return date.toLocaleDateString('en-US', {
                        timeZone: timezone,
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        hour12: false
                    });
                case "30d":
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
    
    // Create linear timescale data with proper gap handling
    createLinearTimescaleData: function(checks, timespan) {
        if (!checks || checks.length === 0) {
            return { labels: [], values: [], statuses: [] };
        }
        
        const now = new Date();
        let startTime;
        let timeInterval;
        
        // Determine time interval and start time based on timespan
        switch (timespan) {
            case "1h":
                startTime = new Date(now.getTime() - 60 * 60 * 1000);
                timeInterval = 60 * 1000; // 1 minute
                break;
            case "6h":
                startTime = new Date(now.getTime() - 6 * 60 * 60 * 1000);
                timeInterval = 5 * 60 * 1000; // 5 minutes
                break;
            case "24h":
                startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                timeInterval = 15 * 60 * 1000; // 15 minutes
                break;
            case "7d":
                startTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                timeInterval = 2 * 60 * 60 * 1000; // 2 hours
                break;
            case "30d":
                startTime = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                timeInterval = 6 * 60 * 60 * 1000; // 6 hours
                break;
            default:
                startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                timeInterval = 15 * 60 * 1000; // 15 minutes
        }
        
        const labels = [];
        const values = [];
        const statuses = [];
        
        // Create a map of timestamps to check data for quick lookup
        const checkMap = new Map();
        checks.forEach(check => {
            const checkTime = new Date(check.timestamp);
            checkMap.set(checkTime.getTime(), {
                response_time: check.response_time,
                status: check.status
            });
        });
        
        // Generate linear timeline with actual data points and null for gaps
        for (let currentTime = startTime.getTime(); currentTime <= now.getTime(); currentTime += timeInterval) {
            const currentDate = new Date(currentTime);
            
            // Find the closest check within the time interval
            let closestCheck = null;
            let minTimeDiff = timeInterval; // Only accept checks within the interval
            
            checkMap.forEach((checkData, checkTimestamp) => {
                const timeDiff = Math.abs(checkTimestamp - currentTime);
                if (timeDiff <= minTimeDiff && checkData.response_time !== null) {
                    closestCheck = checkData;
                    minTimeDiff = timeDiff;
                }
            });
            
            labels.push(this.formatLabelForTimespan(currentDate.toISOString(), timespan));
            values.push(closestCheck ? closestCheck.response_time : null);
            statuses.push(closestCheck ? closestCheck.status : null);
        }
        
        return { labels, values, statuses };
    }
};