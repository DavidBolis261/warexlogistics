# 🚀 Driver API Deployment Checklist

Follow these steps in order to deploy the Driver API to Railway and make it available to real users.

## ✅ Pre-Deployment Checklist

- [ ] Code is pushed to GitHub (main branch)
- [ ] All dependencies in requirements.txt
- [ ] Environment variables documented
- [ ] API tested locally

## 📋 Step-by-Step Deployment

### 1️⃣ Create New Railway Service (5 minutes)

1. Go to: https://railway.app/dashboard
2. Open your existing `warexlogistics` project
3. Click **"+ New"** button (top right)
4. Select **"GitHub Repo"**
5. Choose repository: `DavidBolis261/warexlogistics`
6. Railway will start building automatically

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 2️⃣ Configure Service Settings (3 minutes)

**In the new service:**

1. Click on the service name to rename it:
   - Rename to: `driver-api`

2. Go to **Settings** tab:
   - **Root Directory:** `WebPlatform`
   - **Start Command:** `python driver_api_server.py`
   - **Watch Paths:** Leave as default

3. Click **Save** (if needed)

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 3️⃣ Add Environment Variables (5 minutes)

**In driver-api service → Variables tab:**

Copy these from your existing Streamlit service:

```
WMS_CLUSTER=<your-value>
WMS_INSTANCE_CODE=<your-value>
WMS_TENANT_CODE=<your-value>
WMS_WAREHOUSE_CODE=<your-value>
WMS_API_KEY=<your-value>
GOOGLE_PLACES_API_KEY=<your-value>
```

**How to copy from Streamlit service:**
1. Open your Streamlit service
2. Go to Variables tab
3. Copy each value
4. Paste into driver-api service Variables tab

**⚠️ Note:** Don't set `PORT` - Railway sets this automatically!

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 4️⃣ Deploy and Get URL (2 minutes)

1. Railway should auto-deploy after adding variables
2. If not, click **Deploy** button
3. Wait for build to complete (usually 1-2 minutes)
4. Once deployed, click **Settings** → **Networking**
5. Click **Generate Domain**
6. Copy your URL - it will look like:
   ```
   https://driver-api-production-xyz.up.railway.app
   ```

**Your API URL:** `___________________________________`

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 5️⃣ Test the Deployment (3 minutes)

**Test in browser:**
1. Open: `https://your-api-url.railway.app/health`
   - Should see: `{"status": "healthy", ...}`

2. Open: `https://your-api-url.railway.app/api/driver/docs`
   - Should see API documentation JSON

**Test with script:**
```bash
cd /Users/davidbolis/Desktop/warexlogistics/WebPlatform
./test_api.sh https://your-api-url.railway.app
```

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 6️⃣ Create Test Driver in Dashboard (2 minutes)

1. Open your live dashboard: https://app.warexlogistics.com.au
2. Go to **Drivers** page
3. Click **Add New Driver**
4. Enter:
   - **Name:** Test Driver
   - **Phone:** `0412345678` ← **This is the login!**
   - **Vehicle Type:** Van
   - **License Plate:** TEST-123
   - **Primary Zone:** CBD
   - **Status:** Available
5. Click **Add Driver**

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 7️⃣ Test Login API (2 minutes)

**Using curl:**
```bash
curl -X POST https://your-api-url.railway.app/api/driver/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "0412345678"}'
```

**Expected response:**
```json
{
  "success": true,
  "token": "eyJhbGc...",
  "driver": {
    "id": "DRV-XXX",
    "name": "Test Driver",
    ...
  }
}
```

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 8️⃣ Update iOS App (5 minutes)

**File to update:**
```
/Users/davidbolis/Desktop/Desktop - David's Mac mini/Projects/SydneyMetroCourier/SydneyMetroCourier/APIService.swift
```

**Change line 17 from:**
```swift
static let baseURL = "http://localhost:5000"
```

**To:**
```swift
static let baseURL = "https://your-api-url.railway.app"
```

**⚠️ Important:** Remove `http://` and use `https://` for production!

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 9️⃣ Test iOS App (5 minutes)

1. Open Xcode project
2. Build and run on simulator or device
3. Login with phone: `0412345678`
4. Should see driver profile loaded
5. Check if runs/orders appear (if any assigned)

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

### 🔟 Create Real Driver and Test (10 minutes)

1. **In Dashboard:**
   - Go to Drivers page
   - Add a real driver with their actual phone number
   - Example: `0412 XXX XXX` (use real format)

2. **Create Test Order:**
   - Go to Orders page
   - Create a test order
   - Assign it to the driver you just created

3. **Create a Run:**
   - Go to Route Planning
   - Select driver's zone
   - Select the test order
   - Assign to the driver
   - Click "Create Run"

4. **Test on iOS:**
   - Login with driver's phone number
   - Should see the run and order
   - Try marking order as delivered
   - Check dashboard updates

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

## 🎯 Post-Deployment Verification

### All Systems Check

- [ ] Dashboard accessible at: https://app.warexlogistics.com.au
- [ ] API accessible at: https://your-api-url.railway.app
- [ ] API health check returns 200 OK
- [ ] Can create drivers in dashboard
- [ ] Can login to iOS app with driver phone
- [ ] Orders assigned to driver appear in app
- [ ] Can update delivery status from app
- [ ] Updates reflect in dashboard immediately

### Monitor for 24 Hours

- [ ] Check Railway logs for errors
- [ ] Monitor API response times
- [ ] Verify no CORS errors from iOS
- [ ] Test on both WiFi and cellular data
- [ ] Verify database is persisting data

---

## 🐛 Troubleshooting

### Issue: API returns 500 error

**Check:**
1. Railway logs: `railway logs --service driver-api`
2. Environment variables are all set
3. Database file exists and is accessible

**Fix:**
- Review error in logs
- Verify all env vars from Streamlit service are copied
- Restart the service

---

### Issue: iOS app can't connect

**Check:**
1. API URL in `APIService.swift` is correct
2. Using `https://` not `http://`
3. No typos in URL
4. API health endpoint works in browser

**Fix:**
- Double-check URL spelling
- Ensure using production URL, not localhost
- Test API endpoint in browser first

---

### Issue: Driver can't login

**Check:**
1. Driver exists in dashboard
2. Phone number matches exactly
3. No extra spaces in phone number
4. API receives the request (check logs)

**Fix:**
- Verify phone format in database
- Check API logs for actual error
- Try creating new test driver with simple phone like `0400000000`

---

### Issue: Orders don't appear in app

**Check:**
1. Orders are assigned to the driver
2. Driver ID matches
3. Run is created and assigned to driver
4. API /runs endpoint works (test with curl)

**Fix:**
- Verify order status is `allocated` or `in_transit`
- Check `driver_id` field in database matches
- Test API endpoints manually with curl

---

## 📞 Need Help?

**Railway Issues:**
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

**Check These First:**
1. Railway logs for errors
2. Environment variables are set correctly
3. Both services (dashboard + API) are running
4. Database is shared between services

---

## ✅ Deployment Complete!

When all checkboxes are checked above, your system is live and ready for real users!

**What users can do now:**
1. ✅ Drivers login with their phone number
2. ✅ See assigned delivery runs in real-time
3. ✅ View all delivery stops with addresses
4. ✅ Mark deliveries as complete
5. ✅ View their statistics and profile

**Next enhancements to consider:**
- Push notifications for new orders
- GPS tracking of drivers
- Photo upload for delivery proof
- Digital signature capture
- Offline mode support

---

**Date Completed:** _______________

**Deployed By:** _______________

**Production URL:** _______________

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
