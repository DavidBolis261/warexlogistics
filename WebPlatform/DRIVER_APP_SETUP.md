# Sydney Metro Courier - Driver App Integration Guide

This guide explains how to connect the iOS driver app to the dashboard backend.

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│  iOS Driver App │ <──────>│  Flask REST API  │ <──────>│  SQLite Database│
│  (iPhone/iPad)  │  HTTPS  │  (Port 5000)     │         │  (courier.db)   │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     ▲
                                     │
                                     │
                            ┌────────┴─────────┐
                            │                  │
                            │  Streamlit Admin │
                            │  Dashboard       │
                            │  (Port 8501)     │
                            │                  │
                            └──────────────────┘
```

## Backend Setup

### 1. Install Dependencies

```bash
cd /Users/davidbolis/Desktop/warexlogistics/WebPlatform
python3 -m pip install flask flask-cors
```

### 2. Start the Driver API Server

The API server runs separately from the Streamlit dashboard:

```bash
python3 driver_api_server.py
```

You should see:

```
============================================================
🚚 Sydney Metro Courier - Driver API Server
============================================================

✅ Server starting on http://0.0.0.0:5000
📱 Mobile app can connect to: http://localhost:5000/api/driver/...
📚 API docs available at: http://localhost:5000/api/driver/docs
💚 Health check at: http://localhost:5000/health

============================================================
```

### 3. Test the API

Test that the API is working:

```bash
# Health check
curl http://localhost:5000/health

# API documentation
curl http://localhost:5000/api/driver/docs
```

### 4. Create a Test Driver

In the Streamlit dashboard (running on port 8501):

1. Go to **Drivers** page
2. Add a new driver with these details:
   - Name: Test Driver
   - Phone: `0412345678` ← **This is the login ID for the app**
   - Vehicle Type: Van
   - License Plate: ABC-123
   - Primary Zone: CBD
   - Status: Available

## iOS App Setup

### 1. Add APIService.swift to Xcode Project

1. Open the Xcode project:
   ```bash
   open "/Users/davidbolis/Desktop/Desktop - David's Mac mini/Projects/SydneyMetroCourier/SydneyMetroCourier.xcodeproj"
   ```

2. In Xcode, right-click on the `SydneyMetroCourier` folder
3. Select **Add Files to "SydneyMetroCourier"...**
4. Navigate to and select `APIService.swift`
5. Make sure "Copy items if needed" is checked
6. Click **Add**

### 2. Configure API URL

The API service is currently configured for local development:

**For Testing on Simulator:**
- The app will connect to `http://localhost:5000`
- This works because the simulator shares the same network as your Mac

**For Testing on Physical iPhone:**
1. Find your Mac's local IP address:
   ```bash
   ipconfig getifaddr en0
   ```
   Example output: `192.168.1.100`

2. Update `APIService.swift` line 17:
   ```swift
   static let baseURL = "http://192.168.1.100:5000"  // Use your Mac's IP
   ```

**For Production:**
- Deploy the Flask API to Railway/Heroku/etc
- Update the baseURL to your production URL

### 3. Update App Transport Security (for local development)

To allow HTTP connections during development:

1. Open `Info.plist` in Xcode
2. Add the following:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

⚠️ **Remove this before publishing to App Store!** Use HTTPS in production.

### 4. Update LoginView.swift

The login now uses phone number instead of driver ID. Update the LoginView to integrate with the API:

Replace the mock login logic with actual API calls using the `APIService`.

## How Authentication Works

### Driver Login Flow

1. **Driver enters phone number** in the iOS app (e.g., `0412345678`)
2. **App sends request** to `POST /api/driver/login` with phone number
3. **Backend validates** phone number against drivers table
4. **Backend returns**:
   - Auth token (valid for 30 days)
   - Driver profile data
   - Expiration timestamp
5. **App stores token** in UserDefaults
6. **All subsequent requests** include the token in Authorization header

### Token Management

- Tokens are stored locally on the device
- Tokens expire after 30 days
- Users must re-login after expiration
- Logout invalidates the token on the server

## API Endpoints Reference

### Authentication

#### POST /api/driver/login
Login with phone number

**Request:**
```json
{
  "phone": "0412345678"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "driver": {
    "id": "DRV-123",
    "name": "Test Driver",
    "phone": "0412345678",
    "vehicleType": "Van",
    "plateNumber": "ABC-123",
    "rating": 4.8,
    "totalDeliveries": 150,
    "successRate": 0.967,
    "status": "available",
    "currentZone": "CBD"
  },
  "expires_at": "2024-02-15T12:00:00"
}
```

### Delivery Runs

#### GET /api/driver/runs
Get all runs assigned to the driver

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `status` (optional): Filter by status (active, pending, completed)

**Response:**
```json
{
  "runs": [
    {
      "id": "RUN-240215-001",
      "runNumber": "RUN-240215-001",
      "zone": "CBD",
      "date": "2024-02-15T08:00:00",
      "status": "active",
      "totalStops": 12,
      "completedStops": 3,
      "estimatedDuration": 7200,
      "totalDistance": 24.5
    }
  ],
  "total": 1
}
```

#### GET /api/driver/runs/{run_id}/stops
Get all delivery stops for a specific run

**Response:**
```json
{
  "stops": [
    {
      "id": "SMC-45231",
      "sequenceNumber": 1,
      "status": "delivered",
      "order": {
        "id": "SMC-45231",
        "orderNumber": "SMC-45231",
        "customer": {
          "id": "C001",
          "name": "John Smith",
          "phone": "0423456789",
          "email": "john@email.com"
        },
        "address": {
          "street": "123 George Street",
          "suburb": "Sydney",
          "postcode": "2000",
          "state": "NSW",
          "latitude": -33.8688,
          "longitude": 151.2093
        },
        "parcels": 2,
        "serviceLevel": "express",
        "specialInstructions": "Leave at front door",
        "createdAt": "2024-02-15T08:00:00"
      }
    }
  ],
  "total": 12
}
```

### Update Delivery Status

#### POST /api/driver/stops/{stop_id}/update
Update the status of a delivery stop

**Request:**
```json
{
  "status": "delivered",
  "notes": "Left with receptionist"
}
```

**For failed deliveries:**
```json
{
  "status": "failed",
  "failureReason": "notHome",
  "notes": "No answer at door, attempted twice"
}
```

**Failure Reasons:**
- `notHome` - Customer Not Home
- `wrongAddress` - Wrong Address
- `refused` - Delivery Refused
- `damaged` - Parcel Damaged
- `accessIssue` - Cannot Access Location
- `other` - Other

### Driver Profile

#### GET /api/driver/profile
Get driver profile and statistics

**Response:**
```json
{
  "driver": {
    "id": "DRV-123",
    "name": "Test Driver",
    ...
  },
  "stats": {
    "deliveriesToday": 15,
    "totalDeliveries": 150,
    "successRate": 0.967,
    "activeOrders": 8
  }
}
```

## Testing the Integration

### 1. Start Both Servers

Terminal 1 - API Server:
```bash
cd /Users/davidbolis/Desktop/warexlogistics/WebPlatform
python3 driver_api_server.py
```

Terminal 2 - Streamlit Dashboard:
```bash
cd /Users/davidbolis/Desktop/warexlogistics/WebPlatform
streamlit run app.py
```

### 2. Create Test Data

In the dashboard:
1. Create a driver with phone `0412345678`
2. Create some orders
3. Assign orders to the driver
4. Create a delivery run for the driver

### 3. Test iOS App

1. Run the app in Xcode simulator
2. Login with phone `0412345678`
3. You should see:
   - Your driver profile
   - Active delivery runs
   - All delivery stops
   - Ability to mark deliveries as complete

## Deployment

### Backend API Deployment (Railway)

1. The Flask API server needs to run separately from Streamlit
2. You can deploy it to Railway as a separate service
3. Update the iOS app's `APIConfig.baseURL` to your production URL

### iOS App Deployment

1. Change `APIConfig.baseURL` to production URL
2. Remove NSAppTransportSecurity settings from Info.plist
3. Ensure production API uses HTTPS
4. Build and submit to App Store

## Troubleshooting

### "Network Error" on Login

- **Check API server is running:** Visit http://localhost:5000/health
- **Check phone number:** Must match exactly what's in the dashboard
- **Check firewall:** Make sure port 5000 is not blocked

### "Driver Not Found"

- Verify driver exists in dashboard with that exact phone number
- Phone numbers must match exactly (including spaces/formatting)

### iOS Can't Connect (Physical Device)

- Use your Mac's local IP instead of `localhost`
- Ensure iPhone and Mac are on the same WiFi network
- Check Mac firewall isn't blocking port 5000

### Token Expired

- Tokens last 30 days
- Driver needs to log in again
- Clear app data and re-login

## Next Steps

1. **Add Push Notifications:** Notify drivers of new orders
2. **Add GPS Tracking:** Track driver location in real-time
3. **Add Photo Upload:** Allow drivers to upload delivery photos
4. **Add Signature Capture:** Digital signatures for deliveries
5. **Add Offline Mode:** Cache data for offline operation

## Support

For issues or questions, check:
- API logs: Check terminal running `driver_api_server.py`
- iOS logs: Check Xcode console
- Database: Use `sqlite3 courier.db` to inspect data
