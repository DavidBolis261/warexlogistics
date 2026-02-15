# Driver API Service

This is the REST API for the Sydney Metro Courier mobile driver app.

## Railway Deployment

**Root Directory:** `DriverAPI`

The service will automatically use the settings in `railway.json` and run:
```
python driver_api_server.py
```

## Environment Variables Required

Copy these from your Streamlit service:
- `WMS_CLUSTER`
- `WMS_INSTANCE_CODE`
- `WMS_TENANT_CODE`
- `WMS_WAREHOUSE_CODE`
- `WMS_API_KEY`
- `GOOGLE_PLACES_API_KEY`

## Local Development

```bash
cd DriverAPI
python driver_api_server.py
```

API will be available at http://localhost:5000
