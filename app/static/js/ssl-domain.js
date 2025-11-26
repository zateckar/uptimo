
// Uptimo JavaScript - SSL Certificate and Domain Information Management
// This file contains SSL, domain, and DNS information display functionality

// Enhanced SSL Certificate and Domain Information Manager
const SSLDomainManager = {
    // Initialize the SSL/Domain/DNS dashboard
    initialize: function() {
        this.setupEventListeners();
        this.setupKeyboardNavigation();
    },
    
    // Setup event listeners for the enhanced dashboard
    setupEventListeners: function() {
        // Sort functionality
        const sortBySelect = document.getElementById('sortBySelect');
        if (sortBySelect) {
            sortBySelect.addEventListener('change', (e) => {
                this.sortSections(e.target.value);
            });
        }
        
        // Refresh data button
        const refreshBtn = document.getElementById('refreshDataBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllData();
            });
        }
        
        // Setup collapse/expand behavior with summary view
        this.setupCollapseBehavior();
    },
    
    // Setup keyboard navigation for accessibility
    setupKeyboardNavigation: function() {
        document.querySelectorAll('.collapsible-section .card-header').forEach(header => {
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    header.click();
                }
            });
        });
    },
    
    // Setup collapse behavior with summary view
    setupCollapseBehavior: function() {
        document.querySelectorAll('.collapsible-section').forEach(section => {
            const collapseElement = section.querySelector('.collapse');
            const summaryBody = section.querySelector('.summary-body');
            
            if (collapseElement && summaryBody) {
                collapseElement.addEventListener('show.bs.collapse', () => {
                    summaryBody.classList.add('d-none');
                    section.classList.remove('showing-summary');
                });
                
                collapseElement.addEventListener('hide.bs.collapse', () => {
                    summaryBody.classList.remove('d-none');
                    section.classList.add('showing-summary');
                });
            }
        });
    },
    
    // Sort sections based on selected criteria
    sortSections: function(sortBy) {
        const container = document.getElementById('sslDomainSection');
        if (!container) return;
        
        const sections = Array.from(container.querySelectorAll('.ssl-domain-item'));
        
        sections.sort((a, b) => {
            switch (sortBy) {
                case 'expiration-asc':
                    return this.extractExpirationDays(a) - this.extractExpirationDays(b);
                case 'expiration-desc':
                    return this.extractExpirationDays(b) - this.extractExpirationDays(a);
                case 'name':
                    return this.getSectionName(a).localeCompare(this.getSectionName(b));
                case 'status':
                    return this.getSectionStatus(a).localeCompare(this.getSectionStatus(b));
                default:
                    return 0;
            }
        });
        
        // Re-append sorted sections
        sections.forEach(section => container.appendChild(section));
    },
    
    // Extract expiration days from section data
    extractExpirationDays: function(section) {
        const expiration = section.dataset.expiration;
        return expiration ? parseInt(expiration) : 999999;
    },
    
    // Get section name for sorting
    getSectionName: function(section) {
        const header = section.querySelector('h6');
        return header ? header.textContent.trim() : '';
    },
    
    // Get section status for sorting
    getSectionStatus: function(section) {
        const badge = section.querySelector('.badge');
        return badge ? badge.textContent.trim() : '';
    },
    
    // Refresh all SSL/Domain/DNS data
    refreshAllData: function() {
        const refreshBtn = document.getElementById('refreshDataBtn');
        if (refreshBtn) {
            const icon = refreshBtn.querySelector('i');
            icon.classList.add('fa-spin');
        }
        
        if (Uptimo.state.selectedMonitorId) {
            MonitorManager.loadDetails(Uptimo.state.selectedMonitorId).finally(() => {
                if (refreshBtn) {
                    const icon = refreshBtn.querySelector('i');
                    icon.classList.remove('fa-spin');
                }
            });
        }
    },
    
    updateSSLAndDomainInfo: function(monitor, recentChecks) {
        // Find latest data for each type independently
        const sslInfo = this.findLatestData(recentChecks, 'ssl_info');
        const domainInfo = this.findLatestData(recentChecks, 'domain_info');
        const dnsInfo = this.findLatestData(recentChecks, 'dns_info');
        
        this.updateSSLAndDomainInfoFromData(monitor, sslInfo, domainInfo, dnsInfo);
    },

    updateSSLAndDomainInfoFromData: function(monitor, sslInfo, domainInfo, dnsInfo) {
        const sslDomainSection = document.getElementById("sslDomainSection");
        const dnsSection = document.getElementById("dnsSection");
        
        // Check if monitor supports SSL/domain info
        const supportsSSL = this.supportsSSLInfo(monitor);
        const supportsDomain = this.supportsDomainInfo(monitor);
        
        if (!supportsSSL && !supportsDomain) {
            // Hide both sections if not supported
            if (sslDomainSection) sslDomainSection.classList.add("d-none");
            if (dnsSection) dnsSection.classList.add("d-none");
            return;
        }
        
        if (!sslInfo && !domainInfo && !dnsInfo) {
            this.showNoDataMessage(supportsSSL, supportsDomain);
            return;
        }
        
        // Update SSL Certificate information
        if (supportsSSL && sslInfo) {
            this.updateSSLInfo(sslInfo);
        } else if (supportsSSL) {
            this.showSSLInfoError("No SSL certificate data available");
        }
        
        // Update Domain Registration information
        if (supportsDomain && domainInfo) {
            this.updateDomainInfo(domainInfo);
        } else if (supportsDomain) {
            this.showDomainInfoError("No domain registration data available");
        }
        
        // Update DNS information
        if (supportsDomain && dnsInfo) {
            this.updateDNSInfo(dnsInfo);
        } else if (supportsDomain) {
            this.showDNSInfoError("No DNS data available");
        }
        
        // Show sections if they have data
        if (supportsSSL || supportsDomain) {
            if (sslDomainSection) sslDomainSection.classList.remove("d-none");
            if (dnsSection && supportsDomain) dnsSection.classList.remove("d-none");
        }
    },
    
    findLatestData: function(recentChecks, key) {
        if (!recentChecks || recentChecks.length === 0) return null;
        
        // Find the most recent check that has the specific data key
        const check = recentChecks.find(check =>
            check.additional_data && check.additional_data[key]
        );
        
        return check ? check.additional_data[key] : null;
    },
    
    supportsSSLInfo: function(monitor) {
        // HTTPS monitors always support SSL
        if (monitor.type === 'https' || (monitor.type === 'http' && monitor.target.startsWith('https://'))) {
            return true;
        }
        
        // Kafka monitors support SSL when using SSL or SASL_SSL security protocols
        if (monitor.type === 'kafka') {
            const securityProtocol = monitor.kafka_security_protocol || '';
            return securityProtocol === 'SSL' || securityProtocol === 'SASL_SSL';
        }
        
        return false;
    },
    
    supportsDomainInfo: function(monitor) {
        return ['https', 'http', 'tcp', 'ping'].includes(monitor.type);
    },
    
    
    showNoDataMessage: function(supportsSSL, supportsDomain) {
        const sslDomainSection = document.getElementById("sslDomainSection");
        const dnsSection = document.getElementById("dnsSection");
        
        if (supportsSSL) {
            this.showSSLInfoError("No SSL certificate data available. Monitor may not have been checked yet.");
        }
        
        if (supportsDomain) {
            this.showDomainInfoError("No domain registration data available. Monitor may not have been checked yet.");
            this.showDNSInfoError("No DNS data available. Monitor may not have been checked yet.");
        }
        
        if (supportsSSL || supportsDomain) {
            if (sslDomainSection) sslDomainSection.classList.remove("d-none");
            if (dnsSection && supportsDomain) dnsSection.classList.remove("d-none");
        }
    },
    
    updateSSLInfo: function(sslInfo) {
        const container = document.getElementById("sslCertificateInfo");
        const statusBadge = document.getElementById("sslStatus");
        const summaryElement = document.getElementById("sslSummary");
        const summaryBody = document.getElementById("sslSummaryBody");
        
        if (!container || !statusBadge) return;
        
        try {
            if (sslInfo.error) {
                this.showSSLInfoError(sslInfo.error);
                statusBadge.textContent = "ERROR";
                statusBadge.className = "badge bg-danger";
                this.updateSSLSummary("ERROR", null);
                return;
            }
            
            // Update status badge
            const daysToExpiration = sslInfo.days_to_expiration || 0;
            let statusText, statusClass;
            if (daysToExpiration < 0) {
                statusText = "EXPIRED";
                statusClass = "bg-danger";
            } else if (daysToExpiration <= 7) {
                statusText = "EXPIRING SOON";
                statusClass = "bg-warning";
            } else {
                statusText = "VALID";
                statusClass = "bg-success";
            }
            
            statusBadge.textContent = statusText;
            statusBadge.className = `badge ${statusClass}`;
            
            // Update summary
            this.updateSSLSummary(statusText, daysToExpiration);
            
            // Build SSL info HTML
            let html = '<div class="ssl-info">';
            
            // Subject information
            if (sslInfo.subject) {
                html += '<div class="mb-2">';
                html += '<strong>Subject:</strong><br>';
                
                // Handle both object and array formats for subject
                let subject = sslInfo.subject;
                if (Array.isArray(subject)) {
                    // If it's an array, try to convert to object or extract common fields
                    // This handles cases where backend might return raw tuples
                    const subjectObj = {};
                    subject.forEach(item => {
                        if (Array.isArray(item) && item.length > 0) {
                            // Handle [['key', 'value']] format
                            const pair = item[0];
                            if (Array.isArray(pair) && pair.length >= 2) {
                                subjectObj[pair[0]] = pair[1];
                            }
                        }
                    });
                    // If we extracted anything, use it
                    if (Object.keys(subjectObj).length > 0) {
                        subject = subjectObj;
                    }
                }
                
                // Common fields
                if (subject.commonName) {
                    html += `<small class="text-muted">Common Name:</small> ${this.escapeHtml(subject.commonName)}<br>`;
                }
                if (subject.organizationName) {
                    html += `<small class="text-muted">Organization:</small> ${this.escapeHtml(subject.organizationName)}<br>`;
                }
                if (subject.organizationalUnitName) {
                    html += `<small class="text-muted">Organizational Unit:</small> ${this.escapeHtml(subject.organizationalUnitName)}<br>`;
                }
                if (subject.countryName) {
                    html += `<small class="text-muted">Country:</small> ${this.escapeHtml(subject.countryName)}<br>`;
                }
                if (subject.localityName) {
                    html += `<small class="text-muted">Locality:</small> ${this.escapeHtml(subject.localityName)}<br>`;
                }
                if (subject.stateOrProvinceName) {
                    html += `<small class="text-muted">State/Province:</small> ${this.escapeHtml(subject.stateOrProvinceName)}<br>`;
                }
                html += '</div>';
            }
            
            // Issuer information
            if (sslInfo.issuer) {
                html += '<div class="mb-2">';
                html += '<strong>Issuer:</strong><br>';
                
                let issuer = sslInfo.issuer;
                // Similar handling for issuer if it's an array
                if (Array.isArray(issuer)) {
                    const issuerObj = {};
                    issuer.forEach(item => {
                        if (Array.isArray(item) && item.length > 0) {
                            const pair = item[0];
                            if (Array.isArray(pair) && pair.length >= 2) {
                                issuerObj[pair[0]] = pair[1];
                            }
                        }
                    });
                    if (Object.keys(issuerObj).length > 0) {
                        issuer = issuerObj;
                    }
                }

                if (issuer.commonName) {
                    html += `<small class="text-muted">Common Name:</small> ${this.escapeHtml(issuer.commonName)}<br>`;
                }
                if (issuer.organizationName) {
                    html += `<small class="text-muted">Organization:</small> ${this.escapeHtml(issuer.organizationName)}<br>`;
                }
                if (issuer.countryName) {
                    html += `<small class="text-muted">Country:</small> ${this.escapeHtml(issuer.countryName)}<br>`;
                }
                html += '</div>';
            }
            
            // Validity period
            html += '<div class="mb-2">';
            html += '<strong>Validity Period:</strong><br>';
            if (sslInfo.not_before) {
                html += `<small class="text-muted">Issued:</small> ${this.escapeHtml(sslInfo.not_before)}<br>`;
            }
            if (sslInfo.not_after) {
                html += `<small class="text-muted">Expires:</small> ${this.escapeHtml(sslInfo.not_after)}<br>`;
            }
            if (daysToExpiration !== null) {
                const expirationClass = daysToExpiration < 0 ? 'text-danger' :
                                    daysToExpiration <= 7 ? 'text-warning' : 'text-success';
                html += `<small class="text-muted">Days to Expiration:</small> <span class="${expirationClass}">${daysToExpiration}</span><br>`;
            }
            html += '</div>';
            
            // Additional details
            if (sslInfo.version) {
                html += `<div class="mb-1"><small class="text-muted">Version:</small> ${sslInfo.version}</div>`;
            }
            if (sslInfo.serial_number) {
                html += `<div class="mb-1"><small class="text-muted">Serial Number:</small> ${sslInfo.serial_number}</div>`;
            }
            if (sslInfo.signature_algorithm) {
                html += `<div class="mb-1"><small class="text-muted">Signature Algorithm:</small> ${this.escapeHtml(sslInfo.signature_algorithm)}</div>`;
            }
            if (sslInfo.public_key_algorithm) {
                html += `<div class="mb-1"><small class="text-muted">Public Key Algorithm:</small> ${this.escapeHtml(sslInfo.public_key_algorithm)}</div>`;
            }
            
            // Subject Alternative Names
            if (sslInfo.subject_alt_name && Array.isArray(sslInfo.subject_alt_name) && sslInfo.subject_alt_name.length > 0) {
                html += '<div class="mb-2">';
                html += '<strong>Subject Alternative Names:</strong><br>';
                sslInfo.subject_alt_name.forEach(san => {
                    html += `<small class="text-muted">•</small> ${this.escapeHtml(san)}<br>`;
                });
                html += '</div>';
            }
            
            html += '</div>';
            container.innerHTML = html;
        } catch (e) {
            console.error("Error updating SSL info:", e);
            this.showSSLInfoError("Error displaying SSL information");
        }
    },
    
    showSSLInfoError: function(message) {
        const container = document.getElementById("sslCertificateInfo");
        const statusBadge = document.getElementById("sslStatus");
        
        if (container) {
            container.innerHTML = `<div class="text-center text-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <p class="mt-2 mb-0">${this.escapeHtml(message)}</p>
            </div>`;
        }
        
        if (statusBadge) {
            statusBadge.textContent = "ERROR";
            statusBadge.className = "badge bg-danger";
        }
        
        // Update summary to show error
        this.updateSSLSummary("ERROR", null);
    },
    
    updateDomainInfo: function(domainInfo) {
        const container = document.getElementById("domainRegistrationInfo");
        const statusBadge = document.getElementById("domainStatus");
        
        if (!container || !statusBadge) return;
        
        try {
            if (domainInfo.error) {
                this.showDomainInfoError(domainInfo.error);
                statusBadge.textContent = "ERROR";
                statusBadge.className = "badge bg-danger";
                this.updateDomainSummary("ERROR", null);
                return;
            }
            
            // Calculate days to expiration for status
            const daysToExpiration = domainInfo.days_to_expiration;
            let statusText, statusClass;
            
            if (daysToExpiration !== null && daysToExpiration !== undefined) {
                if (daysToExpiration < 0) {
                    statusText = "EXPIRED";
                    statusClass = "bg-danger";
                } else if (daysToExpiration <= 30) {
                    statusText = "EXPIRING SOON";
                    statusClass = "bg-warning";
                } else {
                    statusText = "ACTIVE";
                    statusClass = "bg-success";
                }
            } else {
                statusText = "ACTIVE";
                statusClass = "bg-info";
            }
            
            // Update status badge
            statusBadge.textContent = statusText;
            statusBadge.className = `badge ${statusClass}`;
            
            // Update summary
            this.updateDomainSummary(statusText, daysToExpiration);
            
            // Build domain info HTML
            let html = '<div class="domain-info">';
            
            // Basic domain information
            if (domainInfo.domain) {
                html += `<div class="mb-2"><strong>Domain:</strong> ${this.escapeHtml(domainInfo.domain)}</div>`;
            }
            
            // Registration information
            if (domainInfo.registrar) {
                html += `<div class="mb-2"><strong>Registrar:</strong> ${this.escapeHtml(domainInfo.registrar)}</div>`;
            }
            
            // Dates
            if (domainInfo.creation_date) {
                // Handle array of dates (some whois servers return multiple)
                let createdDate = domainInfo.creation_date;
                if (Array.isArray(createdDate)) {
                    createdDate = createdDate[0];
                }
                html += `<div class="mb-1"><small class="text-muted">Created:</small> ${this.escapeHtml(createdDate)}</div>`;
            }
            
            if (domainInfo.expiration_date) {
                // Handle array of dates
                let expiryDate = domainInfo.expiration_date;
                if (Array.isArray(expiryDate)) {
                    expiryDate = expiryDate[0];
                }
                html += `<div class="mb-1"><small class="text-muted">Expires:</small> ${this.escapeHtml(expiryDate)}</div>`;
            }
            
            if (domainInfo.updated_date) {
                // Handle array of dates
                let updatedDate = domainInfo.updated_date;
                if (Array.isArray(updatedDate)) {
                    updatedDate = updatedDate[0];
                }
                html += `<div class="mb-1"><small class="text-muted">Last Updated:</small> ${this.escapeHtml(updatedDate)}</div>`;
            }
            
            if (domainInfo.days_to_expiration !== null && domainInfo.days_to_expiration !== undefined) {
                const expirationClass = domainInfo.days_to_expiration < 0 ? 'text-danger' :
                                    domainInfo.days_to_expiration <= 30 ? 'text-warning' : 'text-success';
                html += `<div class="mb-2"><small class="text-muted">Days to Expiration:</small> <span class="${expirationClass}">${domainInfo.days_to_expiration}</span></div>`;
            }
            
            // Name servers
            if (domainInfo.name_servers && Array.isArray(domainInfo.name_servers) && domainInfo.name_servers.length > 0) {
                html += '<div class="mb-2">';
                html += '<strong>Name Servers:</strong><br>';
                domainInfo.name_servers.forEach(ns => {
                    html += `<small class="text-muted">•</small> ${this.escapeHtml(ns)}<br>`;
                });
                html += '</div>';
            }
            
            // Status information
            if (domainInfo.status && Array.isArray(domainInfo.status) && domainInfo.status.length > 0) {
                html += '<div class="mb-2">';
                html += '<strong>Status:</strong><br>';
                domainInfo.status.forEach(status => {
                    html += `<small class="text-muted">•</small> ${this.escapeHtml(status)}<br>`;
                });
                html += '</div>';
            }
            
            // Registrant information (if available)
            if (domainInfo.registrant) {
                html += '<div class="mb-2">';
                html += '<strong>Registrant:</strong><br>';
                if (typeof domainInfo.registrant === 'string') {
                    html += `${this.escapeHtml(domainInfo.registrant)}<br>`;
                } else if (typeof domainInfo.registrant === 'object') {
                    Object.entries(domainInfo.registrant).forEach(([key, value]) => {
                        if (value) {
                            html += `<small class="text-muted">${this.escapeHtml(key)}:</small> ${this.escapeHtml(value)}<br>`;
                        }
                    });
                }
                html += '</div>';
            }

            // Admin Email (if available)
            if (domainInfo.admin_email) {
                html += '<div class="mb-2">';
                html += '<strong>Admin Email:</strong><br>';
                if (Array.isArray(domainInfo.admin_email)) {
                    domainInfo.admin_email.forEach(email => {
                        html += `${this.escapeHtml(email)}<br>`;
                    });
                } else {
                    html += `${this.escapeHtml(domainInfo.admin_email)}<br>`;
                }
                html += '</div>';
            }

            // Tech Email (if available)
            if (domainInfo.tech_email) {
                html += '<div class="mb-2">';
                html += '<strong>Tech Email:</strong><br>';
                if (Array.isArray(domainInfo.tech_email)) {
                    domainInfo.tech_email.forEach(email => {
                        html += `${this.escapeHtml(email)}<br>`;
                    });
                } else {
                    html += `${this.escapeHtml(domainInfo.tech_email)}<br>`;
                }
                html += '</div>';
            }
            
            html += '</div>';
            container.innerHTML = html;
        } catch (e) {
            console.error("Error updating domain info:", e);
            this.showDomainInfoError("Error displaying domain information");
        }
    },
    
    showDomainInfoError: function(message) {
        const container = document.getElementById("domainRegistrationInfo");
        const statusBadge = document.getElementById("domainStatus");
        
        if (container) {
            container.innerHTML = `<div class="text-center text-warning">
                <i class="bi bi-exclamation-triangle"></i>
                <p class="mt-2 mb-0">${this.escapeHtml(message)}</p>
            </div>`;
        }
        
        if (statusBadge) {
            statusBadge.textContent = "ERROR";
            statusBadge.className = "badge bg-danger";
        }
        
        // Update summary to show error
        this.updateDomainSummary("ERROR", null);
    },
    
    updateDNSInfo: function(dnsInfo) {
        const container = document.getElementById("dnsInfo");
        
        if (!container) return;
        
        if (dnsInfo.error) {
            this.showDNSInfoError(dnsInfo.error);
            this.updateDNSSummary(0);
            return;
        }
        
        // Count total DNS records for summary
        let totalRecords = 0;
        if (dnsInfo.a_records) totalRecords += dnsInfo.a_records.length;
        if (dnsInfo.aaaa_records) totalRecords += dnsInfo.aaaa_records.length;
        if (dnsInfo.mx_records) totalRecords += dnsInfo.mx_records.length;
        if (dnsInfo.ns_records) totalRecords += dnsInfo.ns_records.length;
        if (dnsInfo.txt_records) totalRecords += dnsInfo.txt_records.length;
        
        // Update DNS summary
        this.updateDNSSummary(totalRecords);
        
        // Build DNS info HTML
        let html = '<div class="dns-info">';
        
        // A records (IPv4)
        if (dnsInfo.a_records && dnsInfo.a_records.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong>A Records (IPv4):</strong><br>';
            dnsInfo.a_records.forEach(record => {
                html += `<span class="badge bg-secondary me-1">${this.escapeHtml(record)}</span>`;
            });
            html += '</div>';
        }
        
        // AAAA records (IPv6)
        if (dnsInfo.aaaa_records && dnsInfo.aaaa_records.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong>AAAA Records (IPv6):</strong><br>';
            dnsInfo.aaaa_records.forEach(record => {
                html += `<span class="badge bg-secondary me-1">${this.escapeHtml(record)}</span>`;
            });
            html += '</div>';
        }
        
        // MX records (Mail)
        if (dnsInfo.mx_records && dnsInfo.mx_records.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong>MX Records (Mail):</strong><br>';
            dnsInfo.mx_records.forEach(record => {
                html += `<div class="text-muted small">${this.escapeHtml(record)}</div>`;
            });
            html += '</div>';
        }
        
        // NS records (Name Servers)
        if (dnsInfo.ns_records && dnsInfo.ns_records.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong>NS Records (Name Servers):</strong><br>';
            dnsInfo.ns_records.forEach(record => {
                html += `<div class="text-muted small">${this.escapeHtml(record)}</div>`;
            });
            html += '</div>';
        }
        
        // TXT records
        if (dnsInfo.txt_records && dnsInfo.txt_records.length > 0) {
            html += '<div class="mb-3">';
            html += '<strong>TXT Records:</strong><br>';
            dnsInfo.txt_records.forEach(record => {
                html += `<div class="text-muted small" style="word-break: break-all;">${this.escapeHtml(record)}</div>`;
            });
            html += '</div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    },
    
    showDNSInfoError: function(message) {
        const container = document.getElementById("dnsInfo");
        
        if (container) {
            container.innerHTML = `<div class="text-center text-warning">
                <i class="bi bi-exclamation-triangle"></i>
                <p class="mt-2 mb-0">${this.escapeHtml(message)}</p>
            </div>`;
        }
        
        // Update summary to show error
        this.updateDNSSummary(0);
    },
    
    escapeHtml: function(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    },
    
    // Update SSL summary view
    updateSSLSummary: function(status, daysToExpiration) {
        const summaryElement = document.getElementById('sslSummary');
        const summaryBody = document.getElementById('sslSummaryBody');
        
        if (!summaryElement) return;
        
        let statusClass, statusIcon, daysText, daysClass;
        
        if (status === 'ERROR') {
            statusClass = 'bg-danger';
            statusIcon = 'bi-x-circle';
            daysText = 'Error';
            daysClass = 'expired';
        } else if (daysToExpiration < 0) {
            statusClass = 'bg-danger';
            statusIcon
            statusIcon = 'bi-exclamation-triangle';
            daysText = `Expired ${Math.abs(daysToExpiration)} days ago`;
            daysClass = 'expired';
        } else if (daysToExpiration <= 7) {
            statusClass = 'bg-warning';
            statusIcon = 'bi-exclamation-triangle';
            daysText = `${daysToExpiration} days`;
            daysClass = 'warning';
        } else {
            statusClass = 'bg-success';
            statusIcon = 'bi-check-circle';
            daysText = `${daysToExpiration} days`;
            daysClass = 'good';
        }
        
        // Update status badge
        const statusBadge = document.getElementById('sslStatus');
        if (statusBadge) {
            statusBadge.textContent = status;
            statusBadge.className = `badge ${statusClass}`;
        }
        
        // Update summary text
        summaryElement.innerHTML = `
            <span class="summary-days ${daysClass}">
                <i class="bi ${statusIcon} me-1"></i>${daysText}
            </span>
        `;
        
        // Update summary body content
        if (summaryBody) {
            summaryBody.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted">Status:</small>
                        <span class="badge ${statusClass} ms-1">${status}</span>
                    </div>
                    <div>
                        <small class="text-muted">Expires in:</small>
                        <strong class="ms-1 ${daysClass === 'expired' ? 'text-danger' : daysClass === 'warning' ? 'text-warning' : 'text-success'}">${daysText}</strong>
                    </div>
                </div>
            `;
        }
    },
    
    // Update domain summary view
    updateDomainSummary: function(status, daysToExpiration) {
        const summaryElement = document.getElementById('domainSummary');
        const summaryBody = document.getElementById('domainSummaryBody');
        
        if (!summaryElement) return;
        
        let statusClass, statusIcon, daysText, daysClass;
        
        if (status === 'ERROR') {
            statusClass = 'bg-danger';
            statusIcon = 'bi-x-circle';
            daysText = 'Error';
            daysClass = 'expired';
        } else if (daysToExpiration < 0) {
            statusClass = 'bg-danger';
            statusIcon = 'bi-exclamation-triangle';
            daysText = `Expired ${Math.abs(daysToExpiration)} days ago`;
            daysClass = 'expired';
        } else if (daysToExpiration <= 30) {
            statusClass = 'bg-warning';
            statusIcon = 'bi-exclamation-triangle';
            daysText = `${daysToExpiration} days`;
            daysClass = 'warning';
        } else {
            statusClass = 'bg-success';
            statusIcon = 'bi-check-circle';
            daysText = `${daysToExpiration} days`;
            daysClass = 'good';
        }
        
        // Update status badge
        const statusBadge = document.getElementById('domainStatus');
        if (statusBadge) {
            statusBadge.textContent = status;
            statusBadge.className = `badge ${statusClass}`;
        }
        
        // Update summary text
        summaryElement.innerHTML = `
            <span class="summary-days ${daysClass}">
                <i class="bi ${statusIcon} me-1"></i>${daysText}
            </span>
        `;
        
        // Update summary body content
        if (summaryBody) {
            summaryBody.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted">Status:</small>
                        <span class="badge ${statusClass} ms-1">${status}</span>
                    </div>
                    <div>
                        <small class="text-muted">Expires in:</small>
                        <strong class="ms-1 ${daysClass === 'expired' ? 'text-danger' : daysClass === 'warning' ? 'text-warning' : 'text-success'}">${daysText}</strong>
                    </div>
                </div>
            `;
        }
    },
    
    // Update DNS summary view
    updateDNSSummary: function(recordCount) {
        const summaryElement = document.getElementById('dnsSummary');
        const summaryBody = document.getElementById('dnsSummaryBody');
        
        if (!summaryElement) return;
        
        const count = recordCount || 0;
        const statusClass = count > 0 ? 'bg-success' : 'bg-secondary';
        const statusIcon = count > 0 ? 'bi-check-circle' : 'bi-dash-circle';
        
        // Update summary text
        summaryElement.innerHTML = `
            <span class="summary-days good">
                <i class="bi ${statusIcon} me-1"></i>${count} records
            </span>
        `;
        
        // Update summary body content
        if (summaryBody) {
            summaryBody.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted">Status:</small>
                        <span class="badge ${statusClass} ms-1">${count > 0 ? 'Available' : 'No Records'}</span>
                    </div>
                    <div>
                        <small class="text-muted">Total Records:</small>
                        <strong class="ms-1 text-success">${count}</strong>
                    </div>
                </div>
            `;
        }
    }
};