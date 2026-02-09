import streamlit as st


def apply_styles():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }

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

    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: rgba(255,255,255,0.9);
    }

    .section-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(102, 126, 234, 0.3);
    }

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

    .priority-express {
        border-left: 4px solid #ef4444;
    }

    .priority-standard {
        border-left: 4px solid #3b82f6;
    }

    .priority-economy {
        border-left: 4px solid #6b7280;
    }

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
