# PostgreSQL Migration Guide - Production Setup

This guide will migrate your system from SQLite to PostgreSQL for production use.

## Why PostgreSQL?

- ✅ Shared database between Dashboard and Driver API
- ✅ Better for concurrent users
- ✅ Production-grade and reliable
- ✅ Built-in Railway support
- ✅ No file locking issues

## Step 1: Add PostgreSQL to Railway (5 minutes)

### In Railway Dashboard:

1. Go to your project
2. Click **"+ New"** button
3. Select **"Database"**
4. Choose **"PostgreSQL"**
5. Click **"Add PostgreSQL"**

Railway will automatically:
- Create a PostgreSQL database
- Generate credentials
- Add `DATABASE_URL` environment variable to all services

**Note:** The `DATABASE_URL` format will be:
```
postgresql://user:password@host:port/database
```

## Step 2: Add Database Dependencies (Already Done)

Add these to `requirements.txt` (I'll do this):
```
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0
```

## Step 3: Update Code to Support PostgreSQL

The code needs to:
1. Detect if `DATABASE_URL` exists (use PostgreSQL)
2. Otherwise use SQLite (for local development)
3. Create tables on first run

## Step 4: Migrate Existing Data (If Any)

If you have important data in SQLite:
1. Export from SQLite
2. Import to PostgreSQL

For now, since database is empty, we can just start fresh.

## Step 5: Redeploy Both Services

After PostgreSQL is added:
1. Both services will automatically get `DATABASE_URL`
2. Redeploy Streamlit dashboard
3. Redeploy Driver API
4. Both will use the same PostgreSQL database

## Step 6: Test

1. Create driver in dashboard → Should appear in PostgreSQL
2. Login to iOS app → Should find the driver
3. Create orders → Should sync to API
4. Everything connected! ✅

