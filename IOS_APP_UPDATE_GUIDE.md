# iOS App Update Guide - Connect to Live API

This guide shows you exactly which files to update in your iOS app to connect to the live Railway API.

## Files You Need to Update

### 1. APIService.swift ✅ (Already Created)

**Location:** `SydneyMetroCourier/APIService.swift`

**What to change:**
- Line 17: Update baseURL

```swift
// Change FROM:
static let baseURL = "http://localhost:5000"

// Change TO:
static let baseURL = "https://eloquent-cooperation-production-12c5.up.railway.app"
```

---

### 2. LoginView.swift 🔄 (Needs Update)

**Location:** `SydneyMetroCourier/LoginView.swift`

**Problem:** Currently uses mock data instead of real API

**Solution:** Replace the entire file with the updated version

**Where to find updated version:**
```
/Users/davidbolis/Desktop/Desktop - David's Mac mini/Projects/SydneyMetroCourier/SydneyMetroCourier/LoginView_UPDATED.swift
```

**Changes made:**
- ✅ Removed password field (only phone number needed)
- ✅ Calls real API using `APIService.login(phone:)`
- ✅ Handles API errors properly
- ✅ Converts API response to Driver model
- ✅ Stores auth token automatically

**How to update:**
1. Open `LoginView.swift` in Xcode
2. Delete all contents
3. Copy contents from `LoginView_UPDATED.swift`
4. Paste into `LoginView.swift`
5. Save

---

### 3. SydneyMetroCourierApp.swift 🔄 (Needs Update)

**Location:** `SydneyMetroCourier/SydneyMetroCourierApp.swift`

**Problem:** AppState doesn't have `cancellables` property needed for API calls

**Solution:** Replace the entire file with the updated version

**Where to find updated version:**
```
/Users/davidbolis/Desktop/Desktop - David's Mac mini/Projects/SydneyMetroCourier/SydneyMetroCourier/SydneyMetroCourierApp_UPDATED.swift
```

**Changes made:**
- ✅ Added `var cancellables = Set<AnyCancellable>()`
- ✅ Imports Combine framework
- ✅ Clears API token on logout

**How to update:**
1. Open `SydneyMetroCourierApp.swift` in Xcode
2. Delete all contents
3. Copy contents from `SydneyMetroCourierApp_UPDATED.swift`
4. Paste into `SydneyMetroCourierApp.swift`
5. Save

---

### 4. RunsListView.swift 🔄 (Needs Update)

**Location:** `SydneyMetroCourier/RunsListView.swift`

**Problem:** Uses `MockData.todaysRuns` instead of fetching from API

**Solution:** You need to replace the mock data fetch with a real API call

**Current code (line ~12):**
```swift
@State private var runs: [DeliveryRun] = MockData.todaysRuns
```

**Should be:**
```swift
@StateObject private var apiService = APIService.shared
@State private var runs: [DeliveryRun] = []
@State private var isLoading = false

// Add this in onAppear:
.onAppear {
    fetchRuns()
}

private func fetchRuns() {
    isLoading = true
    apiService.fetchRuns(status: "active")
        .receive(on: DispatchQueue.main)
        .sink { completion in
            isLoading = false
        } receiveValue: { response in
            // Convert API response to DeliveryRun models
            runs = response.runs.map { convertToDeliveryRun($0) }
        }
        .store(in: &appState.cancellables)
}

private func convertToDeliveryRun(_ apiRun: RunResponse) -> DeliveryRun {
    // Convert RunResponse to DeliveryRun model
    // This requires fetching stops for each run
    DeliveryRun(
        id: apiRun.id,
        runNumber: apiRun.runNumber,
        zone: apiRun.zone,
        date: ISO8601DateFormatter().date(from: apiRun.date) ?? Date(),
        status: DeliveryRun.RunStatus(rawValue: apiRun.status.capitalized) ?? .pending,
        stops: [],  // Fetch separately
        estimatedDuration: apiRun.estimatedDuration,
        totalDistance: apiRun.totalDistance
    )
}
```

---

## Quick Update Checklist

### Step 1: Add APIService.swift
- [ ] In Xcode, right-click on SydneyMetroCourier folder
- [ ] Select "Add Files to SydneyMetroCourier..."
- [ ] Navigate to and select `APIService.swift`
- [ ] Check "Copy items if needed"
- [ ] Click Add

### Step 2: Update APIService.swift
- [ ] Open `APIService.swift` in Xcode
- [ ] Find line 17 with `static let baseURL =`
- [ ] Change to: `"https://eloquent-cooperation-production-12c5.up.railway.app"`
- [ ] Save (Cmd+S)

### Step 3: Update LoginView.swift
- [ ] Open `LoginView.swift` in Xcode
- [ ] Select All (Cmd+A)
- [ ] Delete
- [ ] Open `LoginView_UPDATED.swift` (in same folder)
- [ ] Select All (Cmd+A)
- [ ] Copy (Cmd+C)
- [ ] Go back to `LoginView.swift`
- [ ] Paste (Cmd+V)
- [ ] Save (Cmd+S)

### Step 4: Update SydneyMetroCourierApp.swift
- [ ] Open `SydneyMetroCourierApp.swift` in Xcode
- [ ] Select All (Cmd+A)
- [ ] Delete
- [ ] Open `SydneyMetroCourierApp_UPDATED.swift` (in same folder)
- [ ] Select All (Cmd+A)
- [ ] Copy (Cmd+C)
- [ ] Go back to `SydneyMetroCourierApp.swift`
- [ ] Paste (Cmd+V)
- [ ] Save (Cmd+S)

### Step 5: Build and Run
- [ ] Build the project (Cmd+B)
- [ ] Fix any errors (should be none if done correctly)
- [ ] Run on simulator (Cmd+R)

---

## Testing the Updated App

### Test 1: Login
1. Launch app in simulator
2. Enter phone number: `0412345678`
3. Tap "Sign In"
4. Should show loading spinner
5. Should login successfully with real driver data

**Expected:** Driver profile from Railway API
**Not Expected:** Mock data (Marcus Chen, etc.)

### Test 2: Verify Real Data
After login, check:
- Driver name matches what's in your dashboard
- Phone number is correct
- Vehicle type matches
- Stats are real (not mock data)

### Test 3: Runs (After RunsListView update)
1. Go to Runs tab
2. Should see runs from your dashboard
3. Should be empty if no runs assigned to driver
4. NOT showing mock "Inner West" or "CBD" runs

---

## Common Issues & Fixes

### Issue: "No such module 'Combine'"
**Fix:** Combine is built into iOS 13+, make sure deployment target is iOS 13.0+
- In Xcode: Project Settings → General → Deployment Info → iOS 13.0

### Issue: "Cannot find 'APIService' in scope"
**Fix:** Make sure APIService.swift is added to the project
- File → Add Files to "SydneyMetroCourier"
- Select APIService.swift
- Check "Copy items if needed"

### Issue: App still shows mock data
**Fix:** Make sure you updated ALL three files:
1. APIService.swift - baseURL changed
2. LoginView.swift - using real API
3. SydneyMetroCourierApp.swift - has cancellables

### Issue: Login fails with "Driver not found"
**Fix:** Create a driver in the dashboard
- Go to https://app.warexlogistics.com.au
- Drivers → Add New Driver
- Phone: 0412345678 (must match exactly)

### Issue: "Invalid URL" error
**Fix:** Check APIService.swift line 17
- Should be: `https://eloquent-cooperation-production-12c5.up.railway.app`
- NOT: `http://localhost:5000`

---

## What's Next After These Updates?

### Immediate Next Steps:
1. Update RunsListView to fetch from API
2. Update RunDetailView to fetch stops from API
3. Update DeliveryView to call update status API
4. Update ProfileView to fetch from API

### Future Enhancements:
1. Add pull-to-refresh on all views
2. Add offline mode with local caching
3. Add push notifications for new orders
4. Add photo upload for delivery proof
5. Add signature capture
6. Add GPS tracking

---

## Need Help?

If you get stuck:

1. **Check Xcode console** for error messages
2. **Check API is working:** Visit https://eloquent-cooperation-production-12c5.up.railway.app/health
3. **Verify driver exists:** Check dashboard for driver with phone 0412345678
4. **Check Railway logs:** View logs in Railway dashboard for API errors

---

## Summary

**Files to update:**
1. ✅ APIService.swift - Add to project + update URL
2. ✅ LoginView.swift - Replace with updated version
3. ✅ SydneyMetroCourierApp.swift - Replace with updated version
4. ⏳ RunsListView.swift - Update later (optional)

**After updates:**
- App will login with real API
- Driver data will be from Railway
- No more mock data on login

**Time estimate:** 10-15 minutes
