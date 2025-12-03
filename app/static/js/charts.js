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
        
        container.innerHTML = `<div class="heartbeat-container">${html} <span class="text-xsmall text-muted"> now</span></div>`;
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
        // Get monitor interval for adaptive bucketing
        const monitorInterval = this.getMonitorInterval();
        const chartData = this.createLinearTimescaleData(filteredChecks, timespan, monitorInterval);
        
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
                const checkTime = new Date(check.timestamp);
                
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
        const upChecks = checks.filter(c => c.status === 'up' && c.response_time !== null);
        const downChecks = checks.filter(c => c.status === 'down');
        const timeoutChecks = downChecks.filter(c => c.response_time === null);
        
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
                const downWithTime = downChecks.filter(c => c.response_time !== null);
                if (downWithTime.length > 0) {
                    const sum = downWithTime.reduce((acc, c) => acc + c.response_time, 0);
                    responseTime = sum / downWithTime.length;
                } else {
                    responseTime = 0; // No response times available
                }
            }
        } else if (dominantStatus === 'up' && upChecks.length > 0) {
            // For ups, use median for better representation of typical values
            const times = upChecks.map(c => c.response_time).sort((a, b) => a - b);
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
        
        buckets.forEach(bucket => {
            labels.push(this.formatLabelForTimespan(
                bucket.start.toISOString(),
                timespan
            ));
            
            if (bucket.assignedCheck) {
                // For timeout checks with null response_time, use 0 to ensure they appear in chart
                // The status will still be "down" so it will be colored red
                const responseTime = bucket.assignedCheck.response_time !== null
                    ? bucket.assignedCheck.response_time
                    : 0;
                values.push(responseTime);
                statuses.push(bucket.assignedCheck.status);
            } else {
                values.push(null);
                statuses.push(null);
            }
        });
        
        return { labels, values, statuses };
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
        
        // Sort checks by timestamp to ensure ordered processing
        const sortedChecks = [...checks].sort((a, b) =>
            new Date(a.timestamp) - new Date(b.timestamp)
        );
        
        // Create time buckets with fixed boundaries
        const buckets = this.createTimeBuckets(startTime, endTime, timeIntervalMs);
        
        // Assign checks to buckets - one check per bucket maximum
        this.assignChecksToBuckets(sortedChecks, buckets);
        
        // Convert buckets to chart data
        const result = this.bucketsToChartData(buckets, timespan);
        
        // Fallback: if no data was assigned, use simple direct mapping
        // This is a safety net for edge cases where bucket assignment fails
        if (result.values.filter(v => v !== null).length === 0 && sortedChecks.length > 0) {
            console.warn('Bucket assignment failed, using fallback direct mapping for chart data');
            return this.createSimpleChartData(sortedChecks, timespan);
        }
        
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
        
        // Calculate the end time aligned to the boundary
        const endTime = new Date(Math.ceil(now.getTime() / alignmentIntervalMs) * alignmentIntervalMs);
        const startTime = new Date(endTime.getTime() - timespanMs);
        
        return { startTime, endTime };
    },
    
    // Simple fallback: direct mapping of checks to chart data
    createSimpleChartData: function(checks, timespan) {
        
        const maxDataPoints = this.getMaxDataPointsForTimespan(timespan);
        
        // If we have too many checks, sample them evenly
        let sampledChecks = checks;
        if (checks.length > maxDataPoints) {
            const step = Math.ceil(checks.length / maxDataPoints);
            sampledChecks = checks.filter((_, index) => index % step === 0);
        }
        
        const labels = [];
        const values = [];
        const statuses = [];
        
        sampledChecks.forEach(check => {
            labels.push(this.formatLabelForTimespan(check.timestamp, timespan));
            // For timeout checks with null response_time, use 0 to ensure they appear in chart
            const responseTime = check.response_time !== null ? check.response_time : 0;
            values.push(responseTime);
            statuses.push(check.status);
        });
        
        return { labels, values, statuses };
    }
};