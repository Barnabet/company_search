# Database Setup Guide

This guide explains how to set up PostgreSQL for the Company Search conversational agent.

## Prerequisites

- PostgreSQL 15+ (local) or Render PostgreSQL (production)
- Python 3.10+ with pip
- Environment variable `DATABASE_URL` configured

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set up Database URL

#### Option A: Render PostgreSQL (Production - Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "PostgreSQL"
3. Configure:
   - **Name**: `company-search-db`
   - **Database**: `company_search`
   - **User**: (auto-generated)
   - **Region**: Select closest to your backend
   - **Plan**: Free (256MB, sufficient for Phase 1)
4. Click "Create Database"
5. Copy the **Internal Database URL** (starts with `postgres://`)
6. Add to your `.env` file or Render environment variables:

```bash
DATABASE_URL=postgres://user:password@host:5432/database
```

**Note**: The code automatically converts `postgres://` to `postgresql+asyncpg://` for SQLAlchemy async compatibility.

#### Option B: Local PostgreSQL (Development)

```bash
# Install PostgreSQL
# macOS: brew install postgresql@15
# Ubuntu: sudo apt-get install postgresql-15
# Windows: Download from https://www.postgresql.org/download/windows/

# Start PostgreSQL
# macOS: brew services start postgresql@15
# Ubuntu: sudo systemctl start postgresql
# Windows: Use pg_admin or Windows Services

# Create database
createdb company_search

# Set DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://localhost/company_search
```

### 3. Run Database Migrations

```bash
cd backend

# Run migrations to create tables
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial schema for conversations and messages
```

### 4. Verify Database Setup

```bash
# Start the API
python api.py

# In another terminal, test health endpoint
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-01-18T12:00:00.000000"
}
```

## Database Schema

### Tables

#### `conversations`
Stores conversation sessions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `status` | ENUM | active, extracting, completed, abandoned |
| `created_at` | TIMESTAMP | Conversation start time |
| `updated_at` | TIMESTAMP | Last modification time |
| `completed_at` | TIMESTAMP | Completion time (nullable) |
| `last_activity` | TIMESTAMP | Last user/agent interaction |
| `extraction_result` | JSONB | Final extracted criteria (nullable) |

**Indexes:**
- `idx_conversation_status` on `status`
- `idx_conversation_last_activity` on `last_activity`
- `idx_conversation_created_at` on `created_at`

#### `messages`
Stores individual messages within conversations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | Foreign key → conversations.id |
| `role` | ENUM | user, assistant, system |
| `content` | TEXT | Message text |
| `created_at` | TIMESTAMP | Message timestamp |
| `sequence_number` | INTEGER | Order within conversation |
| `analysis_result` | JSONB | Agent analysis metadata (nullable) |

**Indexes:**
- `idx_message_conversation_seq` on `(conversation_id, sequence_number)`
- `idx_message_created_at` on `created_at`

**Foreign Keys:**
- `conversation_id` → `conversations.id` (ON DELETE CASCADE)

## Alembic Commands

### Create a New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Show current revision
alembic current

# Show migration history
alembic history
```

### Rollback Migrations

```bash
# Downgrade one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Downgrade to base (drop all tables)
alembic downgrade base
```

## Environment Variables

Required environment variables:

```bash
# PostgreSQL connection string
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Existing variables (keep these)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash-lite
```

## Render Deployment

### Add Database to Render Service

1. Go to your Render backend service
2. Navigate to **Environment**
3. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: (paste Internal Database URL from PostgreSQL service)
4. Click "Save Changes"

### Run Migrations on Render

Option 1: **Manual (via Shell)**
```bash
# In Render dashboard, go to your service → Shell
cd /opt/render/project/src/backend
alembic upgrade head
```

Option 2: **Automatic (via render.yaml)**

Update `backend/render.yaml`:
```yaml
services:
  - type: web
    name: company-search-api
    env: python
    buildCommand: "cd backend && pip install -r requirements.txt && alembic upgrade head"
    startCommand: "cd backend && python api.py"
```

## Troubleshooting

### Error: "DATABASE_URL environment variable is not set"

**Solution**: Add `DATABASE_URL` to your `.env` file or environment variables.

### Error: "FATAL: password authentication failed"

**Solution**: Double-check your DATABASE_URL credentials. For Render, copy the exact URL from the PostgreSQL service dashboard.

### Error: "database does not exist"

**Solution**:
```bash
createdb company_search
# OR if using Render, the database is auto-created
```

### Error: "relation 'conversations' does not exist"

**Solution**: Run migrations:
```bash
alembic upgrade head
```

### Error: "Could not connect to database"

**Solution**:
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL format
- Check network/firewall settings

### Connection Pooling Issues on Render

The code uses `NullPool` to disable connection pooling, which works best with serverless environments like Render. If you encounter connection issues, this is already configured.

## Monitoring

### Check Database Size

```sql
SELECT pg_database_size('company_search') / 1024 / 1024 AS size_mb;
```

### Check Table Row Counts

```sql
SELECT
  'conversations' AS table_name,
  COUNT(*) AS row_count
FROM conversations

UNION ALL

SELECT
  'messages' AS table_name,
  COUNT(*) AS row_count
FROM messages;
```

### Check Active Conversations

```sql
SELECT
  status,
  COUNT(*)
FROM conversations
GROUP BY status;
```

### Find Abandoned Conversations (>30min inactive)

```sql
SELECT
  id,
  created_at,
  last_activity,
  NOW() - last_activity AS inactive_duration
FROM conversations
WHERE status = 'active'
  AND last_activity < NOW() - INTERVAL '30 minutes';
```

## Next Steps

After setting up the database:

1. ✅ Phase 1 Complete: Database infrastructure ready
2. 🚀 Phase 2: Implement agent intelligence (completeness checking, question generation)
3. 🎨 Phase 3: Build chat UI
4. 🚀 Phase 4: Production optimizations

## Support

For issues related to:
- **Render PostgreSQL**: [Render Docs](https://render.com/docs/databases)
- **Alembic**: [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- **SQLAlchemy**: [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
