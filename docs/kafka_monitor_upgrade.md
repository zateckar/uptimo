# Kafka Monitor Upgrade Guide

## Overview

This document describes the database schema changes required to support the expanded Kafka monitor functionality in Uptimo.

## New Features

The Kafka monitor has been enhanced with the following capabilities:

1. **mTLS Authentication**: Support for mutual TLS using custom CA certificates, client certificates, and client keys
2. **OAuth2 Client Credentials**: Support for OAuth2 authentication using client credentials flow
3. **Message Reading**: Ability to read the latest message from a Kafka topic with optional offset auto-commit
4. **Message Writing**: Ability to write JSON messages to a Kafka topic for testing

## Database Schema Changes

The following columns have been added to the `monitor` table:

### Kafka Security & Authentication
- `kafka_security_protocol` (String, default: "PLAINTEXT") - Security protocol: PLAINTEXT, SSL, SASL_SSL, SASL_PLAINTEXT
- `kafka_sasl_mechanism` (String, nullable) - SASL mechanism: PLAIN, SCRAM-SHA-256, SCRAM-SHA-512, OAUTHBEARER
- `kafka_sasl_username` (String, nullable) - Username for PLAIN/SCRAM authentication
- `kafka_sasl_password` (String, nullable) - Password for PLAIN/SCRAM authentication

### OAuth2 Configuration
- `kafka_oauth_token_url` (String, nullable) - OAuth2 token endpoint URL
- `kafka_oauth_client_id` (String, nullable) - OAuth2 client ID
- `kafka_oauth_client_secret` (String, nullable) - OAuth2 client secret

### mTLS Configuration
- `kafka_ssl_ca_cert` (Text, nullable) - PEM-encoded CA certificate
- `kafka_ssl_client_cert` (Text, nullable) - PEM-encoded client certificate
- `kafka_ssl_client_key` (Text, nullable) - PEM-encoded client private key

### Topic Operations
- `kafka_topic` (String, nullable) - Kafka topic for read/write operations
- `kafka_read_message` (Boolean, default: False) - Enable reading latest message
- `kafka_write_message` (Boolean, default: False) - Enable writing test message
- `kafka_message_payload` (Text, nullable) - JSON payload for write operations
- `kafka_autocommit` (Boolean, default: False) - Auto-commit offset when reading

## Migration Process

### For New Installations

No migration is needed. The database schema will be created automatically with all the new fields when the application starts for the first time.

### For Existing Installations

SQLAlchemy with SQLite will automatically detect and add the new columns when the application starts. The process is:

1. **Backup your database** (recommended):
   ```bash
   cp instance/uptimo.db instance/uptimo.db.backup
   ```

2. **Stop the application** if it's running

3. **Update the code** with the new changes

4. **Start the application**:
   ```bash
   uv run python run.py
   ```

SQLAlchemy will automatically add the new columns to existing tables. All new columns are nullable or have default values, so existing monitors will continue to work without modification.

### Verification

After migration, verify the schema by connecting to the database:

```bash
sqlite3 instance/uptimo.db
```

Then run:
```sql
.schema monitor
```

You should see all the new Kafka-related columns in the output.

## Updating Existing Kafka Monitors

Existing Kafka monitors will continue to work with the default PLAINTEXT security protocol. To enable the new features:

1. Edit the monitor in the web interface
2. Configure the desired security settings:
   - For mTLS: Select "SSL" security protocol and provide certificates
   - For OAuth2: Select "SASL_SSL" or "SASL_PLAINTEXT", choose "OAUTHBEARER", and provide OAuth2 credentials
   - For basic SASL: Select SASL protocol, choose mechanism (PLAIN/SCRAM), and provide username/password
3. Enable topic operations if needed:
   - Check "Read Latest Message" and provide a topic name to read from
   - Check "Write Test Message", provide a topic name, and optionally a JSON payload
4. Save the monitor

## Rollback

If you need to rollback:

1. Stop the application
2. Restore the backup database:
   ```bash
   cp instance/uptimo.db.backup instance/uptimo.db
   ```
3. Revert to the previous code version
4. Start the application

## Security Considerations

1. **Sensitive Data**: Passwords, client secrets, and private keys are stored in the database. Ensure your database file is properly secured with appropriate file permissions.

2. **TLS Certificates**: Store certificates securely. Consider using environment variables or a secrets management system for production deployments.

3. **OAuth2 Tokens**: Tokens are fetched on-demand and not stored. Ensure token URLs are accessed over HTTPS.

## Testing

After migration, test your Kafka monitors:

1. Create a test Kafka monitor with basic PLAINTEXT connectivity
2. Test mTLS by configuring SSL with certificates
3. Test SASL authentication with your credentials
4. Test OAuth2 if using OAUTHBEARER
5. Test message reading and writing functionality

## Support

For issues or questions:
- Check the application logs for error messages
- Verify your Kafka broker configuration
- Ensure certificates are in valid PEM format
- Confirm OAuth2 credentials and token URL are correct