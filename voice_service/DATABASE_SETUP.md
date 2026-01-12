# Database Setup Guide

## Overview

The Voice Service now supports PostgreSQL database persistence for conversation continuity. This guide covers both local development and Railway production deployment.

## Quick Summary

- **Local Development**: App runs without database (in-memory only)
- **Railway Production**: App uses Railway PostgreSQL with automatic migrations
- **Database enables**: Conversation history, session resumption, 30-day retention

---

## Railway Production Setup (Recommended)

Your Railway PostgreSQL database is already configured! Here's what you need to do:

### 1. Set Environment Variables in Railway

Go to your Railway project settings and add these environment variables:

```bash
# Enable database persistence
ENABLE_DB_PERSISTENCE=true

# Database URL (Railway will provide this automatically as DATABASE_URL)
# If not auto-provided, use:
DATABASE_URL=postgresql+asyncpg://postgres:MkCBYjPHHLqyKuoyyztZEjLxiIejkBEa@postgres.railway.internal:5432/railway

# Data retention
DATA_RETENTION_DAYS=30
CLEANUP_INTERVAL_HOURS=24
```

### 2. Deploy to Railway

```bash
# Commit all changes
git add .
git commit -m "Add database persistence"
git push

# Railway will automatically:
# 1. Install dependencies (including SQLAlchemy, asyncpg, alembic)
# 2. Run start.sh which runs migrations (alembic upgrade head)
# 3. Start the service
```

### 3. Verify Database Setup

Once deployed, check the Railway logs to see:
```
Running database migrations...
✅ Database migrations completed successfully
Starting FastAPI server...
```

Then visit: `https://your-app.railway.app/health`

You should see:
```json
{
  "service": "healthy",
  "checks": {
    "database": {
      "status": "connected"
    }
  }
}
```

---

## Local Development (Without Database)

For local development, the app runs in **in-memory mode** (no database required).

### Current Configuration

The `.env` file is already set to:
```bash
ENABLE_DB_PERSISTENCE=false
```

This means:
- ✅ App works normally
- ✅ Conversations work during a single session
- ❌ Conversations don't persist after restart
- ❌ No database needed

### To Test Database Locally (Optional)

If you want to test database features locally, you need the **public** Railway connection URL:

1. **Get Public URL from Railway**:
   - Go to Railway Dashboard → PostgreSQL → Connect
   - Look for "Public" connection details
   - Host will be something like: `containers-us-west-xxx.railway.app`
   - Port will be a high number like `12345`

2. **Update `.env`**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:MkCBYjPHHLqyKuoyyztZEjLxiIejkBEa@<PUBLIC_HOST>:<PUBLIC_PORT>/railway
   ENABLE_DB_PERSISTENCE=true
   ```

3. **Run Migrations**:
   ```bash
   .venv/Scripts/alembic upgrade head
   ```

4. **Start Service**:
   ```bash
   .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8008
   ```

---

## How Migrations Work

### On Railway (Automatic)

The `start.sh` script runs migrations before starting the server:

```bash
# Runs during deployment
alembic upgrade head  # Creates/updates database tables
uvicorn app.main:app  # Starts server
```

### Manually (If Needed)

```bash
# Check current migration status
alembic current

# See migration history
alembic history

# Upgrade to latest
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

---

## Database Schema

The database has two tables:

### `sessions` Table
```sql
- session_id (VARCHAR 36, PRIMARY KEY)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- status (VARCHAR 20)
- language (VARCHAR 10)
- mode (VARCHAR 20)
- total_turns (INTEGER)
- last_activity_at (TIMESTAMP)
```

### `turns` Table
```sql
- turn_id (VARCHAR 36, PRIMARY KEY)
- session_id (VARCHAR 36, FOREIGN KEY → sessions)
- timestamp (TIMESTAMP)
- transcript (TEXT)
- reply_text (TEXT)
- audio_path (VARCHAR 500)
- audio_duration_ms (INTEGER)
- processing_time_ms (INTEGER)
- route (VARCHAR 50)
```

---

## Features Enabled by Database

### 1. Conversation Continuity
```
User: "Hi, my name is Bob"
AI: "Hello Bob!"

User: "What's my name?"
AI: "Your name is Bob!"  ✅ Remembers!
```

### 2. Session Resumption
If the server restarts, sessions are loaded from the database:
```python
# Frontend keeps using the same session_id
# Backend loads conversation history from DB
```

### 3. Automatic Cleanup
Every 24 hours, sessions older than 30 days are deleted (configurable).

---

## Troubleshooting

### ❌ "Database persistence disabled"
**Cause**: `ENABLE_DB_PERSISTENCE=false` in environment
**Fix**: Set to `true` and redeploy

### ❌ "could not translate host name"
**Cause**: Using `postgres.railway.internal` from local machine
**Fix**: Use public connection URL (see "Local Development" section)

### ❌ "relation 'sessions' does not exist"
**Cause**: Migrations haven't run
**Fix**: Check Railway logs for migration errors, or run manually: `alembic upgrade head`

### ❌ "greenlet_spawn has not been called"
**Cause**: Using async driver in sync context
**Fix**: Already handled! Alembic uses psycopg2 (sync driver) for migrations

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | None | PostgreSQL connection string |
| `ENABLE_DB_PERSISTENCE` | No | `false` | Enable/disable database features |
| `DATA_RETENTION_DAYS` | No | `30` | Delete sessions older than this |
| `CLEANUP_INTERVAL_HOURS` | No | `24` | How often to run cleanup |
| `DB_POOL_SIZE` | No | `10` | Connection pool size |
| `DB_MAX_OVERFLOW` | No | `20` | Max overflow connections |
| `DB_ECHO` | No | `false` | Log SQL queries (debugging) |

---

## Next Steps

1. ✅ Deploy to Railway with `ENABLE_DB_PERSISTENCE=true`
2. ✅ Verify migrations ran successfully in logs
3. ✅ Test conversation continuity
4. ✅ Monitor database storage in Railway dashboard

The database setup is complete and ready for production! 🎉
