# Railway Deployment Guide - Driver API

This guide explains how to deploy the Driver API as a separate service on Railway.

## Architecture

You will have **TWO** Railway services in the same project:

1. **Streamlit Dashboard** (existing) - Admin interface on port 8501
2. **Driver API** (new) - REST API for mobile app on port 5000

Both services share the same database (courier.db) via Railway volumes.

## Deployment Steps

### Step 1: Create New Service in Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** button
3. Select **"GitHub Repo"**
4. Choose your `warexlogistics` repository
5. Railway will detect the Python app

### Step 2: Configure the Service

#### Service Settings:

1. **Service Name:** `driver-api` (or any name you prefer)

2. **Root Directory:**
   - Click on **Settings** tab
   - Set **Root Directory** to: `WebPlatform`

3. **Start Command:**
   - In **Settings** → **Deploy**
   - Set **Start Command** to: `python driver_api_server.py`

4. **Build Command:**
   - Leave as default or set to: `pip install -r requirements.txt`

### Step 3: Add Environment Variables

Copy these environment variables from your Streamlit service:

**Required Variables:**

```
WMS_CLUSTER=your-cluster-name
WMS_INSTANCE_CODE=your-instance-code
WMS_TENANT_CODE=your-tenant-code
WMS_WAREHOUSE_CODE=your-warehouse-code
WMS_API_KEY=your-api-key
GOOGLE_PLACES_API_KEY=your-google-api-key
```

**API-Specific Variables:**

Railway automatically provides `PORT` - don't set it manually.

### Step 4: Share Database Between Services

Both services need to access the same `courier.db` file.

#### Option A: Use Railway Volumes (Recommended)

1. In Railway dashboard, go to your project
2. Click **"+ New"** → **"Volume"**
3. Name it: `courier-data`
4. Mount it to both services at: `/app/WebPlatform/data`

**For Streamlit Service:**
- Go to service settings → Variables
- Add: `DATABASE_PATH=/app/WebPlatform/data/courier.db`

**For Driver API Service:**
- Go to service settings → Variables
- Add: `DATABASE_PATH=/app/WebPlatform/data/courier.db`

#### Option B: Use External Database (Alternative)

For production, consider using PostgreSQL:
1. Add PostgreSQL plugin to Railway project
2. Update `data_manager.py` to support PostgreSQL
3. Use DATABASE_URL environment variable

### Step 5: Deploy

1. Click **Deploy** button
2. Wait for build to complete
3. Railway will provide a public URL like: `https://driver-api-production-xyz.up.railway.app`

### Step 6: Test the Deployment

Once deployed, test the API:

```bash
# Health check
curl https://your-driver-api-url.railway.app/health

# API docs
curl https://your-driver-api-url.railway.app/api/driver/docs

# Test login (replace with actual driver phone)
curl -X POST https://your-driver-api-url.railway.app/api/driver/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "0412345678"}'
```

### Step 7: Update iOS App

Update the iOS app to use the production URL:

**File:** `APIService.swift` (line 17)

```swift
// Change from:
static let baseURL = "http://localhost:5000"

// To your Railway URL:
static let baseURL = "https://your-driver-api-url.railway.app"
```

## Environment Variables Reference

### Required for Both Services

| Variable | Description | Example |
|----------|-------------|---------|
| `WMS_CLUSTER` | Thomax WMS cluster name | `au-sydney-01` |
| `WMS_INSTANCE_CODE` | Your instance code | `INST001` |
| `WMS_TENANT_CODE` | Your tenant code | `TENANT001` |
| `WMS_WAREHOUSE_CODE` | Warehouse code | `WH001` |
| `WMS_API_KEY` | Thomax API key | `your-secret-key` |
| `GOOGLE_PLACES_API_KEY` | Google Maps API key | `AIza...` |

### Railway Automatic Variables

| Variable | Set By | Description |
|----------|--------|-------------|
| `PORT` | Railway | Port to run on (usually 5000-8000) |
| `RAILWAY_ENVIRONMENT` | Railway | `production` or `development` |
| `RAILWAY_PUBLIC_DOMAIN` | Railway | Your public URL |

## Troubleshooting

### API Returns 500 Error

**Check logs:**
```bash
railway logs --service driver-api
```

**Common issues:**
- Missing environment variables
- Database file not accessible
- Missing dependencies in requirements.txt

### Database Not Shared

**Symptoms:** Changes in dashboard don't appear in API

**Solution:**
- Ensure both services mount the same volume
- Check DATABASE_PATH is set correctly
- Verify both services are using the same database file

### CORS Errors from iOS App

**Symptoms:** iOS can't connect, CORS policy errors

**Solution:**
The API already has CORS enabled for all origins. If issues persist:

1. Check the API URL in iOS app matches Railway URL exactly
2. Ensure using `https://` not `http://`
3. Check Railway logs for actual error

### iOS App Can't Connect

**Check these:**

1. **Correct URL:** Use Railway-provided URL, including `https://`
2. **API is running:** Visit `/health` endpoint in browser
3. **No typos:** Double-check the URL in `APIService.swift`
4. **Network:** iOS device has internet connection

## Monitoring

### View Logs

**In Railway Dashboard:**
1. Select your driver-api service
2. Click **"Deployments"** tab
3. Click on latest deployment
4. View logs in real-time

**Using CLI:**
```bash
railway login
railway link
railway logs --service driver-api
```

### Check Service Health

Monitor these endpoints:
- `https://your-api.railway.app/health` - Health check
- `https://your-api.railway.app/api/driver/docs` - API docs

## Scaling & Performance

### Current Setup
- Single instance per service
- SQLite database (suitable for small-medium workloads)
- Shared volume for database

### For High Traffic

1. **Upgrade to PostgreSQL:**
   - Better for concurrent writes
   - Built-in Railway plugin
   - No file locking issues

2. **Add Redis:**
   - Cache authentication tokens
   - Store session data
   - Faster than file-based storage

3. **Horizontal Scaling:**
   - Multiple API instances
   - Load balancer (Railway provides this)
   - Requires PostgreSQL (SQLite doesn't support this)

## Security Considerations

### Production Checklist

✅ **HTTPS Only:** Railway provides this automatically
✅ **Token Expiration:** Set to 30 days (configurable)
✅ **CORS:** Configured for mobile app access
⚠️ **Rate Limiting:** Consider adding for production
⚠️ **Token Storage:** Currently in-memory (consider Redis)

### Recommended Enhancements

1. **Add Rate Limiting:**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   ```

2. **Use Redis for Tokens:**
   - Persist tokens across restarts
   - Share tokens between API instances
   - Faster than in-memory dict

3. **Add API Monitoring:**
   - Sentry for error tracking
   - LogTail for log aggregation
   - Uptime monitoring service

## Cost Estimation

### Railway Pricing (as of 2024)

**Free Tier:**
- $5 free credit per month
- Suitable for development/testing

**Pro Plan ($20/month):**
- Unlimited projects
- More resources per service
- Required for production

**Your Setup:**
- 2 services (Streamlit + API)
- 1 volume for database
- Estimated: $20-30/month

### Alternative Hosting

- **Render:** Similar pricing, easier setup
- **Fly.io:** Pay per usage, potentially cheaper
- **Heroku:** More expensive but mature platform

## Backup & Restore

### Backup Database

**Using Railway CLI:**
```bash
railway run python -c "import shutil; shutil.copy('courier.db', 'courier_backup.db')"
railway download courier_backup.db
```

**Manual:**
1. Connect to service via SSH
2. Copy courier.db file
3. Download to local machine

### Restore Database

1. Upload backup file to Railway volume
2. Rename to courier.db
3. Restart both services

## Next Steps

After successful deployment:

1. ✅ Test all API endpoints
2. ✅ Update iOS app with production URL
3. ✅ Test iOS app login with real driver
4. ✅ Create test orders and assign to driver
5. ✅ Verify driver can see orders in app
6. ✅ Test delivery status updates
7. ✅ Monitor logs for errors

## Support

**Issues with Railway:**
- Railway docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

**Issues with API:**
- Check logs: `railway logs`
- Review error messages
- Check environment variables are set

## Rollback Plan

If deployment fails:

1. **Revert to previous deployment:**
   - In Railway dashboard → Deployments
   - Click on previous successful deployment
   - Click "Redeploy"

2. **Disable new service:**
   - Pause the driver-api service
   - iOS app will fail gracefully
   - Dashboard continues working

3. **Check logs for errors:**
   - Fix issues locally
   - Test locally first
   - Re-deploy when ready
