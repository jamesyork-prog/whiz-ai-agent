# Database Backup Usage Guide

## Quick Start

### Create a Backup
```bash
./scripts/backup_database.sh
```

This will:
- Detect current database credentials automatically
- Create a timestamped backup in `./backups/`
- Display backup location and size
- Show the restore command

### Example Output
```
=== Database Backup Script ===
Timestamp: 20251119_155102
Database: ranjayDB
Host: localhost:5432
User: ranjay.kumar

✓ Backup completed successfully!

Backup location: ./backups/whizdb_backup_20251119_155102.sql
Backup size: 16K

To restore this backup, run:
  docker exec -i parlant-postgres psql -U ranjay.kumar -d ranjayDB < ./backups/whizdb_backup_20251119_155102.sql
```

## Before Running Migration (Task 9)

**IMPORTANT**: Always backup before running migrations!

```bash
# Step 1: Create backup
./scripts/backup_database.sh

# Step 2: Note the backup filename
# Example: whizdb_backup_20251119_155102.sql

# Step 3: Run migration (Task 9)
docker exec parlant-postgres psql -U ranjay.kumar -d ranjayDB -f /docker-entrypoint-initdb.d/migrate_v2.sql

# Step 4: If migration fails, restore
docker exec -i parlant-postgres psql -U ranjay.kumar -d ranjayDB < ./backups/whizdb_backup_20251119_155102.sql
```

## Features

### Automatic Credential Detection
The script automatically detects credentials from the running PostgreSQL container, so it works with both:
- Old credentials (ranjay.kumar/ranjayDB)
- New credentials (admin/WhizDB)

### Safe Backup Format
Backups include:
- `--clean`: Drops objects before recreating them
- `--if-exists`: Prevents errors if objects don't exist
- `--no-owner`: Makes backup portable
- `--no-privileges`: Excludes privilege grants

### Backup Contents
- All table schemas
- All data
- Indexes
- Constraints
- Views
- Sequences

## Troubleshooting

### Container Not Running
```
Error: PostgreSQL container 'parlant-postgres' is not running
```

**Solution:**
```bash
docker-compose up -d postgres
```

### Permission Denied
```
bash: ./scripts/backup_database.sh: Permission denied
```

**Solution:**
```bash
chmod +x scripts/backup_database.sh
```

## Backup Management

### List All Backups
```bash
ls -lh backups/
```

### Delete Old Backups (30+ days)
```bash
find backups/ -name "whizdb_backup_*.sql" -mtime +30 -delete
```

### Keep Only 5 Most Recent
```bash
ls -t backups/whizdb_backup_*.sql | tail -n +6 | xargs rm -f
```

## Next Steps

After creating a backup, you can proceed with:
- **Task 9**: Run migration on existing database
- **Task 10**: Recreate containers with new credentials
- **Task 11**: Verify database schema

See `scripts/README.md` for more details.
