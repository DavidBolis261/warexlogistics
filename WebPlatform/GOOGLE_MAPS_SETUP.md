# Google Maps Integration Setup

The platform now includes full Google Maps integration for geocoding, routing, and interactive map visualization.

## Features

### 1. **Dashboard Map**
- Shows all active orders (pending, allocated, in_transit) on an interactive map
- Color-coded markers:
  - 🟠 Orange: Pending orders
  - 🔵 Blue: Allocated orders
  - 🟢 Green: In Transit orders
- Click on any marker to see order details (Order ID, Customer, Address, Status)
- Automatically geocodes addresses using Google Geocoding API
- Falls back to suburb coordinates if geocoding fails

### 2. **Route Planning & Visualization**
- Interactive route map showing delivery routes for active runs
- Displays optimized route path between stops
- Numbered markers for each stop (1, 2, 3...)
- Click markers to see stop details (Order ID, Customer, Address)
- Blue route line showing the driving path
- Route summary with total stops, driver name, and zone

## Required Google APIs

You need to enable these APIs in your Google Cloud Console:

1. **Places API** - For address autocomplete in order forms
2. **Geocoding API** - For converting addresses to coordinates
3. **Directions API** - For route visualization and optimization

## Setup Instructions

### Step 1: Get a Google API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **API Key**
5. Copy the generated API key

### Step 2: Enable Required APIs

1. Go to **APIs & Services** > **Library**
2. Search for and enable:
   - **Places API**
   - **Geocoding API**
   - **Directions API**

### Step 3: Secure Your API Key (Recommended)

1. In **Credentials**, click on your API key
2. Under **API restrictions**, select **Restrict key**
3. Choose the APIs you want to allow:
   - Places API
   - Geocoding API
   - Directions API
4. Under **Application restrictions**, you can:
   - Add your domain for HTTP referrer restrictions
   - Or leave unrestricted for development

### Step 4: Add API Key to Your Environment

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your API key:
   ```
   GOOGLE_PLACES_API_KEY=your-actual-api-key-here
   ```

3. Restart your Streamlit application:
   ```bash
   streamlit run app.py
   ```

## Usage

### Dashboard
- Navigate to the **Dashboard** page
- The map will automatically display all active orders
- Hover over markers to see tooltips with order information

### Route Planning
- Navigate to **Route Planning** page
- Create a run by selecting a zone and assigning orders to a driver
- Once a run is created, use the **Active Routes Map** dropdown to select and visualize the route
- The map shows:
  - Numbered stops in delivery order
  - Blue route line connecting all stops
  - Tooltips with detailed information for each stop

## Testing

Run the test script to verify your Google Maps integration:

```bash
python3 test_maps.py
```

This will test:
- Geocoding of sample Sydney addresses
- Route generation between two points
- Polyline decoding

## Troubleshooting

### Map not showing
- Check that your Google API key is set in `.env`
- Verify all three APIs are enabled in Google Cloud Console
- Check browser console for any API errors

### Addresses not geocoding
- Ensure addresses include suburb, state, and postcode
- Check that the Geocoding API is enabled
- Verify API key has permission for Geocoding API

### Routes not displaying
- Ensure Directions API is enabled
- Check that you have at least 2 stops in the run
- Verify orders have valid geocoded addresses

### API quota exceeded
- Google provides free tier with quotas
- Check your usage in Google Cloud Console
- Consider enabling billing for higher quotas if needed

## Cost Considerations

Google Maps APIs have free tiers but may incur costs at scale:

- **Geocoding API**: $5 per 1,000 requests (first 40,000/month free)
- **Directions API**: $5 per 1,000 requests (first 40,000/month free)
- **Maps JavaScript API**: $7 per 1,000 loads (first 28,000/month free)

For development and small-scale use, you'll likely stay within free tier limits.

## Implementation Details

### Caching
- Geocoding results are cached using `@lru_cache(maxsize=500)`
- This reduces API calls for frequently used addresses
- Cache persists for the duration of the application session

### Fallback Strategy
- If geocoding fails, the system falls back to predefined suburb coordinates
- This ensures the map still displays even with API issues

### Map Styling
- Uses Mapbox dark theme for consistency with the application design
- Custom tooltips styled to match the application's color scheme
