# Database Backup Scripts

This directory contains scripts for backing up and managing the PostgreSQL database.

## Backup Script

### Location
`scripts/backup_database.sh`

### Purpose
Creates a timestamped backup of the WhizDB PostgreSQL database before performing migrations or other potentially destructive operations.

### Usage

**From host machine (recommended):**
```bash
./scripts/backup_database.sh
```

**From inside Docker container:**
```bash
docker-compose exec parlant bash /app/scripts/backup_database.sh
```

### Backup Location
Backups are stored in `./backups/` directory with the naming format:
```
whizdb_backup_YYYYMMDD_HHMMSS.sql
```

Example: `whizdb_backup_20250119_143022.sql`

### Features
- ✅ Automatic timestamp generation
- ✅ Creates backup directory if it doesn't exist
- ✅ Works both on host and inside Docker containers
- ✅ Includes `--clean` and `--if-exists` flags for safe restoration
- ✅ Displays backup size and location
- ✅ Shows restore command for convenience
- ✅ Lists recent backups

### Backup Contents
The backup includes:
- All table schemas
- All data from existing tables
- Indexes
- Constraints
- Views

The backup excludes:
- Ownership information (uses `--no-owner`)
- Privilege grants (uses `--no-privileges`)

This makes the backup portable across different PostgreSQL installations.

### Restoring a Backup

**From host machine:**
```bash
docker exec -i parlant-postgres psql -U admin -d WhizDB < backups/whizdb_backup_20250119_143022.sql
```

**From inside container:**
```bash
PGPASSWORD=whiz psql -h localhost -p 5432 -U admin -d WhizDB -f /app/backups/whizdb_backup_20250119_143022.sql
```

### Before Migration Workflow

1. **Backup the database:**
   ```bash
   ./scripts/backup_database.sh
   ```

2. **Verify backup was created:**
   ```bash
   ls -lh backups/
   ```

3. **Run migration:**
   ```bash
   docker exec parlant-postgres psql -U admin -d WhizDB -f /docker-entrypoint-initdb.d/migrate_v2.sql
   ```

4. **If migration fails, restore backup:**
   ```bash
   docker exec -i parlant-postgres psql -U admin -d WhizDB < backups/whizdb_backup_YYYYMMDD_HHMMSS.sql
   ```

### Requirements Satisfied
- **Requirement 8.2**: Backup existing data before migration

### Troubleshooting

**Error: PostgreSQL container is not running**
```bash
docker-compose up -d postgres
```

**Error: Permission denied**
```bash
chmod +x scripts/backup_database.sh
```

**Error: Directory not found**
The script automatically creates the `backups/` directory, but ensure you're running from the project root.

### Backup Retention
Backups are not automatically deleted. To manage disk space:

**List all backups:**
```bash
ls -lh backups/
```

**Delete old backups (older than 30 days):**
```bash
find backups/ -name "whizdb_backup_*.sql" -mtime +30 -delete
```

**Keep only the 5 most recent backups:**
```bash
ls -t backups/whizdb_backup_*.sql | tail -n +6 | xargs rm -f
```
