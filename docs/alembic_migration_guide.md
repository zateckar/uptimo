# Alembic Database Migration Guide

## Overview

This project now uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Alembic provides a robust, version-controlled approach to managing database changes.

## Why Alembic?

SQLAlchemy's `db.create_all()` only creates new tables - it **does not** modify existing tables. Alembic solves this by:
- Tracking schema changes in version-controlled migration files
- Safely applying incremental schema updates
- Supporting rollback if needed
- Automatically detecting model changes

## Setup (Already Complete)

Alembic has been initialized and configured for this project:
- Configuration: `alembic.ini`
- Migration environment: `alembic/env.py`
- Migration scripts: `alembic/versions/`

## Common Commands

### Creating a New Migration

When you modify model classes (e.g., add new fields), generate a migration:

```bash
uv run alembic revision --autogenerate -m "description_of_changes"
```

Example:
```bash
uv run alembic revision --autogenerate -m "add_user_profile_fields"
```

This will:
1. Compare current models with database schema
2. Detect differences
3. Generate a migration file in `alembic/versions/`

### Applying Migrations

To upgrade the database to the latest version:

```bash
uv run alembic upgrade head
```

### Rolling Back

To downgrade to a previous version:

```bash
# Downgrade one step
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>

# Downgrade all the way
uv run alembic downgrade base
```

### Checking Current Version

To see the current database version:

```bash
uv run alembic current
```

### Viewing Migration History

To see all migrations:

```bash
uv run alembic history
```

## Development Workflow

### 1. Modify Models

Edit your model files in `app/models/`:

```python
class Monitor(db.Model):
    # Add new field
    new_field = db.Column(db.String(100))
```

### 2. Generate Migration

```bash
uv run alembic revision --autogenerate -m "add_new_field_to_monitor"
```

### 3. Review Migration

Check the generated file in `alembic/versions/`. Alembic is smart but not perfect - review the SQL:

```python
def upgrade():
    op.add_column('monitor', sa.Column('new_field', sa.String(length=100)))

def downgrade():
    op.drop_column('monitor', 'new_field')
```

### 4. Apply Migration

```bash
uv run alembic upgrade head
```

### 5. Test

Verify the changes work as expected.

## Production Deployment

### Before Deployment

1. **Backup the database**:
   ```bash
   cp instance/uptimo.db instance/uptimo.db.backup
   ```

2. **Test migrations locally** on a copy of production data

3. **Review all migration files** in `alembic/versions/`

### During Deployment

1. Stop the application
2. Backup the database
3. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```
4. Start the application
5. Verify functionality

### Rollback Plan

If something goes wrong:

```bash
# Stop application
# Restore backup
cp instance/uptimo.db.backup instance/uptimo.db

# Or downgrade
uv run alembic downgrade <previous_revision>

# Restart application
```

## Migration File Structure

Each migration file contains:

```python
"""add_kafka_monitor_fields

Revision ID: 156027c76783
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '156027c76783'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Schema changes to apply
    pass

def downgrade():
    # How to reverse the changes
    pass
```

## Troubleshooting

### Migration Conflicts

If you get "Multiple head revisions":

```bash
uv run alembic merge heads -m "merge_heads"
uv run alembic upgrade head
```

### Out-of-Sync Database

If database is out of sync with migrations:

```bash
# Stamp database with current revision
uv run alembic stamp head
```

### Failed Migration

If a migration fails partway:

```bash
# Fix the issue, then re-run
uv run alembic upgrade head

# Or rollback and try again
uv run alembic downgrade -1
# Fix migration file
uv run alembic upgrade head
```

## Best Practices

1. **Always backup** before running migrations
2. **Test migrations** on development/staging first
3. **Review generated migrations** - they may need manual tweaking
4. **Use descriptive names** for migrations
5. **Keep migrations small** - one logical change per migration
6. **Don't modify** migration files after they've been committed
7. **Version control** all migration files

## Example: Adding New Fields

### Step 1: Modify Model

```python
# app/models/monitor.py
class Monitor(db.Model):
    # ... existing fields ...
    
    # New field
    description = db.Column(db.Text)
```

### Step 2: Generate Migration

```bash
uv run alembic revision --autogenerate -m "add_description_to_monitor"
```

### Step 3: Review Generated File

```python
def upgrade():
    op.add_column('monitor', sa.Column('description', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('monitor', 'description')
```

### Step 4: Apply

```bash
uv run alembic upgrade head
```

## Manual Migrations

Sometimes you need to write migrations manually:

```bash
# Create empty migration
uv run alembic revision -m "custom_migration"

# Edit the file
vim alembic/versions/xxx_custom_migration.py
```

Example manual migration:

```python
def upgrade():
    # Add index
    op.create_index('idx_monitor_name', 'monitor', ['name'])
    
    # Modify data
    op.execute("UPDATE monitor SET status = 'active' WHERE status IS NULL")

def downgrade():
    op.drop_index('idx_monitor_name', 'monitor')
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)