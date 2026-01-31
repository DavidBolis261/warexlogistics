# Sydney Metro Courier Dashboard

A comprehensive logistics management dashboard for Sydney metro deliveries. Built with Streamlit for rapid prototyping.

## Features

### 📊 Dashboard
- Real-time overview of all operations
- Key metrics (orders, deliveries, drivers)
- Live delivery map placeholder
- Active runs with progress tracking
- Pending orders requiring attention

### 📋 Order Management
- View all orders with filtering and search
- Bulk order allocation to drivers
- Order status tracking (pending, allocated, in-transit, delivered, failed)
- Service level management (express, standard, economy)

### 🚚 Driver Management
- Driver roster with availability status
- Performance metrics (deliveries, success rate, ratings)
- Vehicle and zone assignment
- Contact information

### 🗺️ Route Planning
- Zone-based run creation
- Order selection for runs
- Driver assignment
- Route optimization options
- Active run monitoring

### 📈 Analytics
- Delivery performance over time
- Zone-based analysis
- Service level distribution
- Driver performance leaderboard
- Export capabilities

### ⚙️ Settings
- General configuration
- Zone management with postcodes
- WMS integration settings (Thomax)
- User management

---

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Run locally

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

---

## Running on Local Network

To view the dashboard on other devices (tablets, phones) on your local network:

### Option 1: Using Streamlit's built-in network serving

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then access from other devices using your computer's local IP address:
- Find your IP: `ipconfig` (Windows) or `ifconfig` / `ip addr` (Mac/Linux)
- Access: `http://YOUR_IP_ADDRESS:8501`

### Option 2: With all recommended settings

```bash
streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false
```

### Finding Your Local IP Address

**macOS:**
```bash
ipconfig getifaddr en0
```

**Linux:**
```bash
hostname -I | awk '{print $1}'
```

**Windows (PowerShell):**
```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"}).IPAddress
```

---

## Quick Start Script

Create a `run.sh` (Mac/Linux) or `run.bat` (Windows) for easy launching:

### Mac/Linux (`run.sh`)
```bash
#!/bin/bash
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}')
echo "Starting Sydney Metro Courier Dashboard..."
echo "Access locally: http://localhost:8501"
echo "Access on network: http://$IP:8501"
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### Windows (`run.bat`)
```batch
@echo off
echo Starting Sydney Metro Courier Dashboard...
echo Access locally: http://localhost:8501
echo Check your IP with 'ipconfig' for network access
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

---

## Firewall Notes

If other devices can't connect, you may need to allow port 8501 through your firewall:

**macOS:** Usually no action needed for local network

**Linux:**
```bash
sudo ufw allow 8501
```

**Windows:**
```powershell
netsh advfirewall firewall add rule name="Streamlit" dir=in action=allow protocol=TCP localport=8501
```

---

## Project Structure

```
courier_dashboard/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

---

## Mock Data

This prototype uses generated mock data for demonstration:
- **50 sample orders** across Sydney suburbs
- **10 sample drivers** with various statuses
- **15 sample delivery runs**

Data regenerates when you click "Refresh Data" in the sidebar.

---

## Next Steps for Production

1. **Backend API** - Replace mock data with FastAPI backend
2. **Database** - PostgreSQL with PostGIS for spatial queries
3. **WMS Integration** - Connect to Thomax .wms API
4. **Real Maps** - Integrate Google Maps or Mapbox
5. **Authentication** - Add user login and role-based access
6. **Mobile App** - Build iOS/Android driver apps

---

## Customization

### Changing the Color Scheme

Edit the CSS variables in `app.py` under the `<style>` section:
- Primary gradient: `#667eea` to `#764ba2`
- Success: `#10b981`
- Warning: `#fbbf24`
- Error: `#ef4444`

### Adding New Zones

Modify the `zone_mapping` dictionary in the `generate_mock_orders()` function.

### Adjusting Mock Data Volume

Change the `n` parameter when calling data generation functions:
```python
st.session_state.orders = generate_mock_orders(100)  # More orders
st.session_state.drivers = generate_mock_drivers(20)  # More drivers
```

---

## License

Prototype for Sydney Metro Courier Infrastructure project.
