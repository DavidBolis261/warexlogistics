"""
Sydney Metro Courier Dashboard
A comprehensive logistics management interface for metro deliveries
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Page configuration
st.set_page_config(
    page_title="Sydney Metro Courier",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
    }
    
    

    
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Custom header */
    .dashboard-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .dashboard-title {
        font-family: 'DM Sans', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .dashboard-subtitle {
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
        margin-top: 0.25rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(102, 126, 234, 0.5);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    
    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        line-height: 1;
    }
    
    .metric-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        color: rgba(255,255,255,0.6);
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-change {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        margin-top: 0.75rem;
    }
    
    .metric-change.positive { color: #10b981; }
    .metric-change.negative { color: #ef4444; }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-pending { background: #fbbf24; color: #1a1a2e; }
    .status-in-transit { background: #3b82f6; color: white; }
    .status-delivered { background: #10b981; color: white; }
    .status-failed { background: #ef4444; color: white; }
    .status-available { background: #10b981; color: white; }
    .status-on-route { background: #3b82f6; color: white; }
    .status-offline { background: #6b7280; color: white; }
    
    /* Data tables */
    .dataframe {
        font-family: 'DM Sans', sans-serif !important;
        background: rgba(255,255,255,0.02) !important;
        border: none !important;
    }
    
    .dataframe th {
        background: rgba(102, 126, 234, 0.2) !important;
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 1px !important;
        padding: 1rem !important;
    }
    
    .dataframe td {
        color: rgba(255,255,255,0.9) !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: rgba(255,255,255,0.9);
    }
    
    /* Section headers */
    .section-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(102, 126, 234, 0.3);
    }
    
    /* Order cards */
    .order-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    
    .order-card:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    .order-id {
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        color: #667eea;
        font-weight: 700;
    }
    
    .order-customer {
        font-family: 'DM Sans', sans-serif;
        font-size: 1rem;
        color: white;
        margin-top: 0.5rem;
    }
    
    .order-address {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.6);
        margin-top: 0.25rem;
    }
    
    /* Driver cards */
    .driver-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .driver-name {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: white;
    }
    
    .driver-vehicle {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        color: rgba(255,255,255,0.5);
        margin-top: 0.25rem;
    }
    
    .driver-stats {
        display: flex;
        gap: 1.5rem;
        margin-top: 1rem;
    }
    
    .driver-stat {
        text-align: center;
    }
    
    .driver-stat-value {
        font-family: 'Space Mono', monospace;
        font-size: 1.25rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .driver-stat-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem;
        color: rgba(255,255,255,0.5);
        text-transform: uppercase;
    }
    
    /* Buttons */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255,255,255,0.02);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        color: rgba(255,255,255,0.6);
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Zone map placeholder */
    .zone-map {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 2rem;
        min-height: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }
    
    .zone-map::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 20% 30%, rgba(102, 126, 234, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(118, 75, 162, 0.1) 0%, transparent 50%);
    }
    
    /* Live indicator */
    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        color: #10b981;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .live-dot {
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    /* Priority indicators */
    .priority-express {
        border-left: 4px solid #ef4444;
    }
    
    .priority-standard {
        border-left: 4px solid #3b82f6;
    }
    
    .priority-economy {
        border-left: 4px solid #6b7280;
    }
    
    /* Toast notifications */
    .toast {
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        font-family: 'DM Sans', sans-serif;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.02);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(102, 126, 234, 0.5);
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# MOCK DATA GENERATION
# ============================================

def generate_mock_orders(n=50):
    """Generate realistic mock order data"""
    suburbs = [
        ("Surry Hills", "2010"), ("Bondi", "2026"), ("Newtown", "2042"),
        ("Paddington", "2021"), ("Glebe", "2037"), ("Marrickville", "2204"),
        ("Redfern", "2016"), ("Rozelle", "2039"), ("Balmain", "2041"),
        ("Pyrmont", "2009"), ("Alexandria", "2015"), ("Waterloo", "2017"),
        ("Darlinghurst", "2010"), ("Potts Point", "2011"), ("Randwick", "2031"),
        ("Coogee", "2034"), ("Maroubra", "2035"), ("Mascot", "2020"),
        ("Leichhardt", "2040"), ("Annandale", "2038")
    ]
    
    first_names = ["James", "Sarah", "Michael", "Emma", "David", "Olivia", "Daniel", "Sophie", "Matthew", "Isabella"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
    
    statuses = ["pending", "allocated", "in_transit", "delivered", "failed"]
    status_weights = [0.15, 0.20, 0.30, 0.30, 0.05]
    
    service_levels = ["express", "standard", "economy"]
    service_weights = [0.2, 0.6, 0.2]
    
    orders = []
    base_time = datetime.now() - timedelta(hours=8)
    
    for i in range(n):
        suburb, postcode = random.choice(suburbs)
        status = random.choices(statuses, weights=status_weights)[0]
        service = random.choices(service_levels, weights=service_weights)[0]
        
        order_time = base_time + timedelta(minutes=random.randint(0, 480))
        
        orders.append({
            "order_id": f"SMC-{random.randint(10000, 99999)}",
            "customer": f"{random.choice(first_names)} {random.choice(last_names)}",
            "address": f"{random.randint(1, 200)} {random.choice(['King', 'Queen', 'George', 'Elizabeth', 'Victoria', 'Crown', 'Oxford', 'Park'])} St",
            "suburb": suburb,
            "postcode": postcode,
            "status": status,
            "service_level": service,
            "parcels": random.randint(1, 5),
            "created_at": order_time,
            "driver_id": f"DRV-{random.randint(100, 110)}" if status in ["allocated", "in_transit", "delivered"] else None,
            "eta": (order_time + timedelta(hours=random.randint(1, 4))).strftime("%H:%M") if status in ["allocated", "in_transit"] else None
        })
    
    return pd.DataFrame(orders)


def generate_mock_drivers(n=10):
    """Generate realistic mock driver data"""
    names = [
        "Marcus Chen", "Sarah Thompson", "Ahmed Hassan", "Lisa Nguyen",
        "James Wilson", "Maria Garcia", "David Kim", "Emma Roberts",
        "Ryan O'Brien", "Priya Patel"
    ]
    
    vehicles = ["Van", "Truck", "Van", "Van", "Truck", "Van", "Van", "Truck", "Van", "Van"]
    plates = [f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}-{random.randint(100, 999)}" for _ in range(n)]
    
    statuses = ["available", "on_route", "on_route", "on_route", "available", "on_route", "offline", "on_route", "available", "on_route"]
    
    drivers = []
    for i in range(n):
        drivers.append({
            "driver_id": f"DRV-{100 + i}",
            "name": names[i],
            "vehicle_type": vehicles[i],
            "plate": plates[i],
            "status": statuses[i],
            "current_zone": random.choice(["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"]),
            "deliveries_today": random.randint(8, 25),
            "success_rate": round(random.uniform(0.94, 0.99), 2),
            "rating": round(random.uniform(4.5, 5.0), 1),
            "active_orders": random.randint(0, 8) if statuses[i] == "on_route" else 0,
            "phone": f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
        })
    
    return pd.DataFrame(drivers)


def generate_mock_runs(n=15):
    """Generate mock delivery runs"""
    zones = ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"]
    
    runs = []
    for i in range(n):
        total = random.randint(8, 20)
        completed = random.randint(0, total)
        
        runs.append({
            "run_id": f"RUN-{datetime.now().strftime('%y%m%d')}-{i+1:03d}",
            "zone": random.choice(zones),
            "driver_id": f"DRV-{random.randint(100, 109)}",
            "driver_name": random.choice(["Marcus Chen", "Sarah Thompson", "Ahmed Hassan", "Lisa Nguyen", "James Wilson"]),
            "total_stops": total,
            "completed": completed,
            "progress": round(completed / total * 100),
            "estimated_completion": (datetime.now() + timedelta(hours=random.randint(1, 4))).strftime("%H:%M"),
            "status": "active" if completed < total else "completed"
        })
    
    return pd.DataFrame(runs)


# Initialize session state for mock data
if 'orders' not in st.session_state:
    st.session_state.orders = generate_mock_orders(50)
    
if 'drivers' not in st.session_state:
    st.session_state.drivers = generate_mock_drivers(10)
    
if 'runs' not in st.session_state:
    st.session_state.runs = generate_mock_runs(15)


# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0;">
        <div style="font-size: 2.5rem;">📦</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.25rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            Sydney Metro
        </div>
        <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 2px;">
            Courier System
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "📋 Orders", "🚚 Drivers", "🗺️ Route Planning", "📈 Analytics", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Quick filters
    st.markdown("### Quick Filters")
    
    zone_filter = st.multiselect(
        "Zones",
        ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"],
        default=[]
    )
    
    service_filter = st.multiselect(
        "Service Level",
        ["express", "standard", "economy"],
        default=[]
    )
    
    status_filter = st.multiselect(
        "Status",
        ["pending", "allocated", "in_transit", "delivered", "failed"],
        default=[]
    )
    
    st.markdown("---")
    
    # Live status
    st.markdown("""
    <div class="live-indicator">
        <div class="live-dot"></div>
        System Online
    </div>
    """, unsafe_allow_html=True)
    
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.orders = generate_mock_orders(50)
        st.session_state.drivers = generate_mock_drivers(10)
        st.session_state.runs = generate_mock_runs(15)
        st.rerun()


# ============================================
# MAIN CONTENT
# ============================================

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">Sydney Metro Courier</h1>
            <p class="dashboard-subtitle">{datetime.now().strftime('%A, %d %B %Y')} • Operations Dashboard</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# PAGE: DASHBOARD
# ============================================

if page == "📊 Dashboard":
    
    # Key Metrics Row
    orders_df = st.session_state.orders
    drivers_df = st.session_state.drivers
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_orders = len(orders_df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_orders}</div>
            <div class="metric-label">Total Orders</div>
            <div class="metric-change positive">↑ 12% vs yesterday</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pending = len(orders_df[orders_df['status'] == 'pending'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{pending}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-change negative">↓ Needs attention</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        in_transit = len(orders_df[orders_df['status'] == 'in_transit'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{in_transit}</div>
            <div class="metric-label">In Transit</div>
            <div class="metric-change positive">On track</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        delivered = len(orders_df[orders_df['status'] == 'delivered'])
        delivery_rate = round(delivered / total_orders * 100) if total_orders > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{delivery_rate}%</div>
            <div class="metric-label">Delivered</div>
            <div class="metric-change positive">↑ {delivered} completed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        active_drivers = len(drivers_df[drivers_df['status'].isin(['available', 'on_route'])])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{active_drivers}</div>
            <div class="metric-label">Active Drivers</div>
            <div class="metric-change positive">Online now</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Main content area
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown('<div class="section-header">📍 Live Delivery Map</div>', unsafe_allow_html=True)
        
        # Map placeholder with zone visualization
        st.markdown("""
        <div class="zone-map">
            <div style="position: relative; z-index: 1; text-align: center;">
                <div style="font-family: 'DM Sans', sans-serif; font-size: 1.5rem; color: white; margin-bottom: 1rem;">
                    Sydney Metro Zones
                </div>
                <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                    <div style="background: rgba(102, 126, 234, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #667eea; font-weight: 700;">CBD</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">12 active</div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #10b981; font-weight: 700;">Inner West</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">8 active</div>
                    </div>
                    <div style="background: rgba(251, 191, 36, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(251, 191, 36, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #fbbf24; font-weight: 700;">Eastern</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">15 active</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #ef4444; font-weight: 700;">South</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">10 active</div>
                    </div>
                </div>
                <div style="margin-top: 1.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.4);">
                    Map integration pending • Showing zone summary
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Active Runs
        st.markdown('<div class="section-header">🚚 Active Delivery Runs</div>', unsafe_allow_html=True)
        
        runs_df = st.session_state.runs[st.session_state.runs['status'] == 'active'].head(5)
        
        for _, run in runs_df.iterrows():
            progress_color = "#10b981" if run['progress'] > 70 else "#fbbf24" if run['progress'] > 40 else "#3b82f6"
            st.markdown(f"""
            <div class="order-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{run['run_id']}</div>
                        <div class="order-customer">{run['driver_name']} • {run['zone']}</div>
                        <div class="order-address">{run['completed']}/{run['total_stops']} stops • ETA {run['estimated_completion']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: {progress_color}; font-weight: 700;">{run['progress']}%</div>
                    </div>
                </div>
                <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="background: {progress_color}; height: 100%; width: {run['progress']}%; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div class="section-header">🚨 Pending Orders</div>', unsafe_allow_html=True)
        
        pending_orders = orders_df[orders_df['status'] == 'pending'].head(6)
        
        for _, order in pending_orders.iterrows():
            priority_class = f"priority-{order['service_level']}"
            st.markdown(f"""
            <div class="order-card {priority_class}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{order['order_id']}</div>
                        <div class="order-customer">{order['customer']}</div>
                        <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                    </div>
                    <span class="status-badge status-pending">{order['service_level']}</span>
                </div>
                <div style="margin-top: 0.75rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                    {order['parcels']} parcel(s) • {order['created_at'].strftime('%H:%M')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("View All Pending →", use_container_width=True):
            st.session_state.nav_to_orders = True
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">👤 Driver Status</div>', unsafe_allow_html=True)
        
        for _, driver in drivers_df.head(5).iterrows():
            status_class = f"status-{driver['status'].replace('_', '-')}"
            st.markdown(f"""
            <div class="driver-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="driver-name">{driver['name']}</div>
                        <div class="driver-vehicle">{driver['vehicle_type']} • {driver['plate']}</div>
                    </div>
                    <span class="status-badge {status_class}">{driver['status'].replace('_', ' ')}</span>
                </div>
                <div class="driver-stats">
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['deliveries_today']}</div>
                        <div class="driver-stat-label">Today</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['active_orders']}</div>
                        <div class="driver-stat-label">Active</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['rating']}</div>
                        <div class="driver-stat-label">Rating</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============================================
# PAGE: ORDERS
# ============================================

elif page == "📋 Orders":
    st.markdown('<div class="section-header">📋 Order Management</div>', unsafe_allow_html=True)
    
    # Tabs for order views
    tab1, tab2, tab3, tab4 = st.tabs(["All Orders", "Pending Allocation", "In Transit", "Completed"])
    
    orders_df = st.session_state.orders.copy()
    
    # Apply filters from sidebar
    if zone_filter:
        # Map suburbs to zones (simplified)
        zone_mapping = {
            "Inner West": ["Newtown", "Marrickville", "Leichhardt", "Annandale", "Glebe"],
            "Eastern Suburbs": ["Bondi", "Randwick", "Coogee", "Maroubra", "Paddington"],
            "CBD": ["Surry Hills", "Darlinghurst", "Potts Point", "Pyrmont"],
            "South Sydney": ["Alexandria", "Waterloo", "Redfern", "Mascot"],
            "Inner City": ["Rozelle", "Balmain"]
        }
        selected_suburbs = []
        for zone in zone_filter:
            selected_suburbs.extend(zone_mapping.get(zone, []))
        if selected_suburbs:
            orders_df = orders_df[orders_df['suburb'].isin(selected_suburbs)]
    
    if service_filter:
        orders_df = orders_df[orders_df['service_level'].isin(service_filter)]
    
    if status_filter:
        orders_df = orders_df[orders_df['status'].isin(status_filter)]
    
    with tab1:
        # Search and actions
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("🔍 Search orders...", placeholder="Order ID, customer name, or address")
        with col2:
            sort_by = st.selectbox("Sort by", ["Created (newest)", "Created (oldest)", "Service Level", "Status"])
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ New Order", use_container_width=True):
                st.info("Order creation modal would open here")
        
        if search:
            orders_df = orders_df[
                orders_df['order_id'].str.contains(search, case=False) |
                orders_df['customer'].str.contains(search, case=False) |
                orders_df['address'].str.contains(search, case=False)
            ]
        
        # Display orders as expandable cards
        for _, order in orders_df.iterrows():
            status_class = f"status-{order['status'].replace('_', '-')}"
            priority_class = f"priority-{order['service_level']}"
            
            with st.expander(f"{order['order_id']} • {order['customer']} • {order['suburb']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"""
                    **Customer:** {order['customer']}  
                    **Address:** {order['address']}, {order['suburb']} {order['postcode']}  
                    **Parcels:** {order['parcels']}  
                    **Created:** {order['created_at'].strftime('%Y-%m-%d %H:%M')}
                    """)
                    
                    if order['driver_id']:
                        st.markdown(f"**Assigned Driver:** {order['driver_id']}")
                    if order['eta']:
                        st.markdown(f"**ETA:** {order['eta']}")
                
                with col2:
                    st.markdown(f"""
                    <span class="status-badge {status_class}">{order['status'].replace('_', ' ')}</span>
                    <br><br>
                    <span class="status-badge status-{order['service_level']}">{order['service_level']}</span>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if order['status'] == 'pending':
                        if st.button("Allocate", key=f"alloc_{order['order_id']}"):
                            st.info("Allocation dialog would open")
                    elif order['status'] == 'in_transit':
                        if st.button("Track", key=f"track_{order['order_id']}"):
                            st.info("Tracking view would open")
    
    with tab2:
        pending = orders_df[orders_df['status'] == 'pending']
        st.info(f"📦 {len(pending)} orders awaiting allocation")
        
        # Bulk allocation
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_orders = st.multiselect(
                "Select orders for bulk allocation",
                pending['order_id'].tolist()
            )
        with col2:
            driver_options = st.session_state.drivers[st.session_state.drivers['status'] == 'available']['name'].tolist()
            assigned_driver = st.selectbox("Assign to driver", ["Select driver..."] + driver_options)
        
        if st.button("Allocate Selected Orders", disabled=not selected_orders or assigned_driver == "Select driver..."):
            st.success(f"✅ {len(selected_orders)} orders allocated to {assigned_driver}")
        
        # Display pending orders
        for _, order in pending.iterrows():
            st.markdown(f"""
            <div class="order-card priority-{order['service_level']}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{order['order_id']}</div>
                        <div class="order-customer">{order['customer']}</div>
                        <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                        <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                            {order['parcels']} parcel(s) • {order['service_level'].upper()}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        in_transit = orders_df[orders_df['status'] == 'in_transit']
        st.info(f"🚚 {len(in_transit)} orders currently in transit")
        
        for _, order in in_transit.iterrows():
            st.markdown(f"""
            <div class="order-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{order['order_id']}</div>
                        <div class="order-customer">{order['customer']}</div>
                        <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-badge status-in-transit">In Transit</span>
                        <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.9rem; color: #667eea;">
                            ETA {order['eta']}
                        </div>
                    </div>
                </div>
                <div style="margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                        Driver: {order['driver_id']}
                    </div>
                    <div class="live-indicator">
                        <div class="live-dot"></div>
                        Live tracking
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab4:
        completed = orders_df[orders_df['status'].isin(['delivered', 'failed'])]
        delivered_count = len(completed[completed['status'] == 'delivered'])
        failed_count = len(completed[completed['status'] == 'failed'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ {delivered_count} delivered successfully")
        with col2:
            st.error(f"❌ {failed_count} failed deliveries")
        
        for _, order in completed.iterrows():
            status_class = "status-delivered" if order['status'] == 'delivered' else "status-failed"
            st.markdown(f"""
            <div class="order-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{order['order_id']}</div>
                        <div class="order-customer">{order['customer']}</div>
                        <div class="order-address">{order['address']}, {order['suburb']}</div>
                    </div>
                    <span class="status-badge {status_class}">{order['status']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============================================
# PAGE: DRIVERS
# ============================================

elif page == "🚚 Drivers":
    st.markdown('<div class="section-header">🚚 Driver Management</div>', unsafe_allow_html=True)
    
    drivers_df = st.session_state.drivers
    
    # Driver stats summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        available = len(drivers_df[drivers_df['status'] == 'available'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #10b981;">{available}</div>
            <div class="metric-label">Available</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        on_route = len(drivers_df[drivers_df['status'] == 'on_route'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #3b82f6;">{on_route}</div>
            <div class="metric-label">On Route</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        offline = len(drivers_df[drivers_df['status'] == 'offline'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #6b7280;">{offline}</div>
            <div class="metric-label">Offline</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_deliveries = drivers_df['deliveries_today'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_deliveries}</div>
            <div class="metric-label">Total Deliveries</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Driver cards
    col1, col2 = st.columns(2)
    
    for idx, (_, driver) in enumerate(drivers_df.iterrows()):
        status_class = f"status-{driver['status'].replace('_', '-')}"
        
        with col1 if idx % 2 == 0 else col2:
            st.markdown(f"""
            <div class="driver-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="driver-name">{driver['name']}</div>
                        <div class="driver-vehicle">{driver['driver_id']} • {driver['vehicle_type']} • {driver['plate']}</div>
                        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: rgba(255,255,255,0.5); margin-top: 0.25rem;">
                            📍 {driver['current_zone']} • 📞 {driver['phone']}
                        </div>
                    </div>
                    <span class="status-badge {status_class}">{driver['status'].replace('_', ' ')}</span>
                </div>
                <div class="driver-stats">
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['deliveries_today']}</div>
                        <div class="driver-stat-label">Deliveries</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['active_orders']}</div>
                        <div class="driver-stat-label">Active</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{int(driver['success_rate'] * 100)}%</div>
                        <div class="driver-stat-label">Success</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">⭐ {driver['rating']}</div>
                        <div class="driver-stat-label">Rating</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Add new driver section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">➕ Add New Driver</div>', unsafe_allow_html=True)
    
    with st.form("new_driver_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_name = st.text_input("Driver Name")
            new_phone = st.text_input("Phone Number")
        
        with col2:
            new_vehicle = st.selectbox("Vehicle Type", ["Van", "Truck"])
            new_plate = st.text_input("License Plate")
        
        with col3:
            new_zone = st.selectbox("Primary Zone", ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"])
        
        submitted = st.form_submit_button("Add Driver", use_container_width=True)
        if submitted and new_name:
            st.success(f"✅ Driver {new_name} added successfully!")


# ============================================
# PAGE: ROUTE PLANNING
# ============================================

elif page == "🗺️ Route Planning":
    st.markdown('<div class="section-header">🗺️ Route Planning & Optimization</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Zone selection for route planning
        st.markdown("### Create New Run")
        
        selected_zone = st.selectbox(
            "Select Zone",
            ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"]
        )
        
        # Get pending orders for selected zone
        zone_mapping = {
            "Inner West": ["Newtown", "Marrickville", "Leichhardt", "Annandale", "Glebe"],
            "Eastern Suburbs": ["Bondi", "Randwick", "Coogee", "Maroubra", "Paddington"],
            "CBD": ["Surry Hills", "Darlinghurst", "Potts Point", "Pyrmont"],
            "South Sydney": ["Alexandria", "Waterloo", "Redfern", "Mascot"],
            "Inner City": ["Rozelle", "Balmain"]
        }
        
        zone_suburbs = zone_mapping.get(selected_zone, [])
        zone_orders = st.session_state.orders[
            (st.session_state.orders['suburb'].isin(zone_suburbs)) & 
            (st.session_state.orders['status'] == 'pending')
        ]
        
        st.info(f"📦 {len(zone_orders)} pending orders in {selected_zone}")
        
        # Order selection
        selected_order_ids = st.multiselect(
            "Select orders for this run",
            zone_orders['order_id'].tolist(),
            default=zone_orders['order_id'].tolist()[:5] if len(zone_orders) > 0 else []
        )
        
        # Driver assignment
        available_drivers = st.session_state.drivers[st.session_state.drivers['status'] == 'available']
        
        assigned_driver = st.selectbox(
            "Assign Driver",
            ["Auto-assign (nearest)"] + available_drivers['name'].tolist()
        )
        
        # Route options
        col_a, col_b = st.columns(2)
        with col_a:
            optimize_for = st.radio("Optimize for", ["Fastest route", "Shortest distance", "Time windows"])
        with col_b:
            priority = st.radio("Priority handling", ["Express first", "Standard order", "Balanced"])
        
        if st.button("🚀 Generate Optimized Route", use_container_width=True, type="primary"):
            with st.spinner("Calculating optimal route..."):
                import time
                time.sleep(1.5)
            st.success("✅ Route optimized! 12 stops, estimated 2h 45min")
            st.balloons()
    
    with col2:
        st.markdown("### Active Runs")
        
        runs_df = st.session_state.runs[st.session_state.runs['status'] == 'active']
        
        for _, run in runs_df.iterrows():
            progress_color = "#10b981" if run['progress'] > 70 else "#fbbf24" if run['progress'] > 40 else "#3b82f6"
            st.markdown(f"""
            <div class="order-card">
                <div class="order-id">{run['run_id']}</div>
                <div class="order-customer">{run['driver_name']}</div>
                <div class="order-address">{run['zone']} • {run['completed']}/{run['total_stops']} stops</div>
                <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="background: {progress_color}; height: 100%; width: {run['progress']}%;"></div>
                </div>
                <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                    ETA completion: {run['estimated_completion']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Route visualization placeholder
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Route Preview")
    
    st.markdown("""
    <div class="zone-map" style="min-height: 300px;">
        <div style="position: relative; z-index: 1; text-align: center;">
            <div style="font-family: 'DM Sans', sans-serif; font-size: 1.25rem; color: white;">
                Route Visualization
            </div>
            <div style="margin-top: 1rem; font-family: 'Space Mono', monospace; font-size: 0.8rem; color: rgba(255,255,255,0.5);">
                Interactive map with turn-by-turn directions will appear here
            </div>
            <div style="margin-top: 1.5rem; display: flex; gap: 2rem; justify-content: center;">
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #667eea;">12</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">STOPS</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #10b981;">24.5 km</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">DISTANCE</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #fbbf24;">2h 45m</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">EST. TIME</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# PAGE: ANALYTICS
# ============================================

elif page == "📈 Analytics":
    st.markdown('<div class="section-header">📈 Performance Analytics</div>', unsafe_allow_html=True)
    
    # Date range selector
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date = st.date_input("From", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", datetime.now())
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        time_period = st.selectbox("Quick select", ["Last 7 days", "Last 30 days", "This month", "Last quarter"])
    
    # Key performance metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">1,247</div>
            <div class="metric-label">Total Deliveries</div>
            <div class="metric-change positive">↑ 18% vs last period</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">96.3%</div>
            <div class="metric-label">Success Rate</div>
            <div class="metric-change positive">↑ 2.1%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">42min</div>
            <div class="metric-label">Avg Delivery Time</div>
            <div class="metric-change positive">↓ 5min faster</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">4.8</div>
            <div class="metric-label">Customer Rating</div>
            <div class="metric-change positive">↑ 0.2</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">$8.42</div>
            <div class="metric-label">Cost per Delivery</div>
            <div class="metric-change positive">↓ 12%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Deliveries Over Time")
        
        # Generate mock chart data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq='D')
        deliveries = np.random.randint(30, 60, 30) + np.sin(np.arange(30) * 0.3) * 10
        
        chart_data = pd.DataFrame({
            'Date': dates,
            'Deliveries': deliveries.astype(int)
        })
        
        st.line_chart(chart_data.set_index('Date'), use_container_width=True)
    
    with col2:
        st.markdown("### Deliveries by Zone")
        
        zone_data = pd.DataFrame({
            'Zone': ['Inner West', 'Eastern Suburbs', 'CBD', 'South Sydney', 'Inner City'],
            'Deliveries': [312, 428, 287, 156, 64]
        })
        
        st.bar_chart(zone_data.set_index('Zone'), use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Service Level Distribution")
        
        service_data = pd.DataFrame({
            'Service': ['Express', 'Standard', 'Economy'],
            'Count': [249, 748, 250]
        })
        
        st.bar_chart(service_data.set_index('Service'), use_container_width=True)
    
    with col2:
        st.markdown("### Driver Performance")
        
        driver_perf = st.session_state.drivers[['name', 'deliveries_today', 'success_rate', 'rating']].copy()
        driver_perf.columns = ['Driver', 'Deliveries', 'Success %', 'Rating']
        driver_perf['Success %'] = (driver_perf['Success %'] * 100).round(1)
        
        st.dataframe(
            driver_perf.sort_values('Deliveries', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    
    # Export options
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.download_button(
            "📥 Export CSV",
            data="sample,data,export",
            file_name="analytics_export.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            "📊 Export PDF Report",
            data="sample pdf data",
            file_name="analytics_report.pdf",
            mime="application/pdf"
        )


# ============================================
# PAGE: SETTINGS
# ============================================

elif page == "⚙️ Settings":
    st.markdown('<div class="section-header">⚙️ System Settings</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["General", "Zones & Routing", "Integrations", "Users"])
    
    with tab1:
        st.markdown("### General Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Company Name", value="Sydney Metro Courier")
            st.text_input("Primary Contact Email", value="ops@sydneymetrocourier.com.au")
            st.text_input("Support Phone", value="1300 DELIVER")
        
        with col2:
            st.selectbox("Timezone", ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane"])
            st.selectbox("Date Format", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
            st.selectbox("Default Service Level", ["standard", "express", "economy"])
        
        st.markdown("### Operating Hours")
        
        col1, col2 = st.columns(2)
        with col1:
            st.time_input("Start Time", datetime.strptime("06:00", "%H:%M"))
        with col2:
            st.time_input("End Time", datetime.strptime("21:00", "%H:%M"))
        
        st.multiselect(
            "Operating Days",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        )
    
    with tab2:
        st.markdown("### Delivery Zones")
        
        zones = [
            {"name": "CBD", "postcodes": "2000, 2010, 2011", "surcharge": 0},
            {"name": "Inner West", "postcodes": "2037, 2040, 2041, 2042, 2043, 2044", "surcharge": 0},
            {"name": "Eastern Suburbs", "postcodes": "2021, 2022, 2024, 2025, 2026", "surcharge": 5},
            {"name": "South Sydney", "postcodes": "2015, 2016, 2017, 2018, 2020", "surcharge": 0},
            {"name": "Inner City", "postcodes": "2039, 2041", "surcharge": 0},
        ]
        
        for zone in zones:
            with st.expander(f"📍 {zone['name']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.text_input("Postcodes", value=zone['postcodes'], key=f"pc_{zone['name']}")
                with col2:
                    st.number_input("Surcharge ($)", value=zone['surcharge'], key=f"sc_{zone['name']}")
        
        if st.button("➕ Add New Zone"):
            st.info("Zone creation dialog would open")
        
        st.markdown("### Routing Preferences")
        
        st.slider("Max stops per run", 5, 30, 15)
        st.slider("Max run duration (hours)", 2, 8, 4)
        st.checkbox("Avoid toll roads", value=False)
        st.checkbox("Prioritize express deliveries", value=True)
    
    with tab3:
        st.markdown("### WMS Integration (Thomax)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("API Endpoint", value="https://api.thomax.com.au/v1")
            st.text_input("API Key", value="••••••••••••••••", type="password")
        
        with col2:
            st.selectbox("Sync Frequency", ["Real-time", "Every 5 minutes", "Every 15 minutes", "Hourly"])
            st.selectbox("Sync Mode", ["Push & Pull", "Pull only", "Push only"])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Test Connection"):
                st.success("✅ Connection successful!")
        with col2:
            if st.button("📥 Force Sync Now"):
                st.info("Syncing orders from WMS...")
        
        st.markdown("---")
        
        st.markdown("### Notification Services")
        
        st.checkbox("SMS notifications (Twilio)", value=True)
        st.checkbox("Email notifications (SendGrid)", value=True)
        st.checkbox("Push notifications (Firebase)", value=False)
        
        st.markdown("---")
        
        st.markdown("### Maps & Routing")
        
        st.selectbox("Maps Provider", ["Google Maps", "HERE Maps", "Mapbox"])
        st.text_input("Maps API Key", value="••••••••••••••••", type="password")
    
    with tab4:
        st.markdown("### User Management")
        
        users = [
            {"name": "Admin User", "email": "admin@smc.com.au", "role": "Administrator", "status": "Active"},
            {"name": "Dispatch Manager", "email": "dispatch@smc.com.au", "role": "Dispatcher", "status": "Active"},
            {"name": "Operations Lead", "email": "ops@smc.com.au", "role": "Manager", "status": "Active"},
        ]
        
        for user in users:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.text(user['name'])
            with col2:
                st.text(user['email'])
            with col3:
                st.text(user['role'])
            with col4:
                st.button("Edit", key=f"edit_{user['email']}")
        
        st.markdown("---")
        
        if st.button("➕ Add New User"):
            st.info("User creation dialog would open")
    
    # Save button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        st.success("✅ Settings saved successfully!")


# Footer
st.markdown("""
<div style="text-align: center; padding: 2rem; margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1);">
    <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.3);">
        Sydney Metro Courier Dashboard v1.0 • Built with Streamlit • Prototype Mode
    </div>
</div>
""", unsafe_allow_html=True)
