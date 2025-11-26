# Data Retention

Uptimo includes a comprehensive data retention system to automatically clean up old monitoring data and manage database size.

## Features

### Automated Cleanup
- **Daily scheduled cleanup** at 2 AM UTC
- **Configurable retention periods** for different data types
- **Safe cleanup** (only resolved incidents are deleted)
- **Comprehensive logging** of cleanup operations

### Data Types and Default Retention

| Data Type | Default Retention | Description |
|-----------|-------------------|-------------|
| Check Results | 365 days (configurable via `DATA_RETENTION_DAYS`) | Individual monitor check results with response times, status codes, and errors |
| Incidents | 2x check_results (730 days by default) | Monitor downtime incidents. Only resolved incidents are cleaned up |
| Notification Logs | 90 days | History of sent notifications for debugging and audit |

### Configuration

#### Environment Variables
```bash
# Main retention period (applies to check_results)
DATA_RETENTION_DAYS=365

# Automatically cleaned up via scheduler
```

## Usage

### Web Interface (Admin Only)

1. Navigate to **Admin → Data Retention** in the web interface
2. View current database statistics
3. Review and modify retention policies
4. Estimate cleanup impact before running
5. Trigger manual cleanup if needed

### CLI Commands

All commands can be run with `flask retention <command>`.

#### View Statistics
```bash
# Show current database statistics
flask retention stats

# Output example:
Database Statistics
====================

Check Results:
  Total records: 1,234,567
  Oldest record: 2023-01-01
  Newest record: 2024-01-15

Incidents:
  Total records: 123
  Active count: 2

Notification Logs:
  Total records: 45,678

Retention Policies:
  check_results: 365 days
  incidents: 730 days
  notification_logs: 90 days
```

#### Estimate Cleanup Impact
```bash
# Estimate what would be deleted
flask retention estimate

# Output example:
Cleanup Impact Estimation
=========================
Total estimated deletions: 23,456

Check Results:
  Records to delete: 15,234
  Retention period: 365 days
  Cutoff date: 2023-01-15T10:30:00Z

Incidents:
  Records to delete: 8,222
  Retention period: 730 days
  Cutoff date: 2022-01-15T10:30:00Z

(Use --dry-run with cleanup command for more details)
```

#### Run Cleanup
```bash
# Preview what would be deleted (dry run)
flask retention cleanup --dry-run

# Clean all data types
flask retention cleanup

# Clean specific data type
flask retention cleanup --type check_results
flask retention cleanup --type incidents
flask retention cleanup --type notification_logs

# Override retention days for this run
flask retention cleanup --type check_results --days 180
```

#### Manage Retention Policies
```bash
# Set custom retention for a data type
flask retention set-policy check_results 180
flask retention set-policy notification_logs 60

# Policies can be overridden at runtime
flask retention cleanup --type check_results --days 90
```

### API Endpoints

#### Get Database Statistics
```http
GET /api/admin/data-retention/stats
Authorization: Bearer <token> (admin only)
```

#### Estimate Cleanup Impact
```http
GET /api/admin/data-retention/estimate
Authorization: Bearer <token> (admin only)
```

#### Trigger Cleanup
```http
POST /api/admin/data-retention/cleanup
Content-Type: application/json
Authorization: Bearer <token> (admin only)

{
  "type": "all",  // all, check_results, incidents, notification_logs
  "days_to_keep": 365  // Optional: override default retention
}
```

#### Manage Policies
```http
# Get current policies
GET /api/admin/data-retention/policies

# Update policies
PUT /api/admin/data-retention/policies
Content-Type: application/json

{
  "policies": {
    "check_results": 365,
    "incidents": 730,
    "notification_logs": 90
  }
}
```

## Implementation Details

### Service Architecture

- **DataRetentionService**: Core service handling all retention logic
- **Background Scheduler**: Automated daily cleanup at 2 AM UTC
- **API Layer**: REST endpoints for admin management
- **CLI Interface**: Command-line tools for maintenance
- **Web Interface**: Admin dashboard for visual management

### Safety Features

1. **Protected Data**: Active incidents are never deleted
2. **Transaction Safety**: All deletions use database transactions
3. **Logging**: Comprehensive logging of all cleanup operations
4. **Estimate Before Execute**: Preview impact before actual deletion
5. **Atomic Operations**: Rollback on any failure during cleanup

### Performance Considerations

- **Batch Deletion**: Uses efficient bulk delete operations
- **Index Optimization**: Database indexes support time-based queries
- **Non-blocking**: Cleanup runs in background scheduler
- **Configurable Timing**: Cleanup time can be adjusted to suit traffic patterns

### Monitoring and Logging

Cleanup operations are logged with:
- Number of records deleted
- Data types cleaned
- Retention periods used
- Execution time
- Any errors encountered

Example log entry:
```
INFO:app.services.data_retention:Cleaned up 15,234 old check results (older than 365 days)
INFO:app.services.data_retention:Cleaned up 8,222 old resolved incidents (older than 730 days)
INFO:app.schedulers.monitor_scheduler:Data cleanup completed successfully. Deleted 23,456 records
```

## Best Practices

### Production Deployment

1. **Monitor Cleanup Logs**: Check that daily cleanup is running successfully
2. **Database Monitoring**: Watch database size trends
3. **Performance Impact**: Monitor cleanup execution time
4. **Backup Strategy**: Ensure backups before major retention policy changes

### Retention Policy Planning

1. **Business Requirements**: Align with compliance and operational needs
2. **Storage Capacity**: Consider available disk space and growth
3. **Performance Impact**: Balance between data retention and query performance
4. **Audit Requirements**: Keep notification logs for adequate audit periods

### Emergency Procedures

```bash
# If database is full, run immediate cleanup with shorter retention
flask retention cleanup --type check_results --days 30
flask retention cleanup --type notification_logs --days 7

# If cleanup is stuck, check scheduler status
flask scheduler status

# Manually stop and restart scheduler if needed
flask scheduler stop
flask scheduler start
```

## Troubleshooting

### Common Issues

1. **Cleanup Not Running**: Check scheduler is started and no errors in logs
2. **High Memory Usage**: Large deletions may need to be batched - consider shorter retention periods
3. **Performance Impact**: Run cleanup during low-traffic periods (default 2 AM UTC)
4. **Disk Space**: Monitor disk usage and adjust retention accordingly

### Debug Commands

```bash
# Check scheduler status
flask scheduler status

# Test scheduler job execution
flask scheduler test-job data_cleanup

# Manual verification of cleanup
flask retention cleanup --dry-run --type check_results
```

## Configuration Examples

### Development Environment
```bash
# Shorter retention for development
DATA_RETENTION_DAYS=30
```

### Production Environment
```bash
# Longer retention for production analytics
DATA_RETENTION_DAYS=730
```

### High-Volume Monitoring
```bash
# Shorter retention for high-volume systems
DATA_RETENTION_DAYS=90
```

### Compliance-Focused
```bash
# Extended retention for compliance requirements
DATA_RETENTION_DAYS=2555  # 7 years

# Keep notification logs even longer for audit
# (set via API or web interface)
```

This data retention system provides flexible, automated cleanup while ensuring important data is preserved and system performance remains optimal.