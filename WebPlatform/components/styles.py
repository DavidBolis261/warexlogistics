"""Warex visual system: readable surfaces, compact navigation and gold accents."""
import streamlit as st


def apply_styles(authenticated=False):
    st.markdown('''<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    :root { --ink:#17212f; --muted:#64748b; --line:#e4e8ee; --gold:#d99b00; }
    html,body,[data-testid="stApp"] {font-family:'DM Sans',sans-serif; color:var(--ink);}
    .stApp {background:#f5f7fa;}
    [data-testid="stAppViewContainer"] > .main {background:#f5f7fa;}
    [data-testid="stMainBlockContainer"],.main .block-container {padding:2rem 2.5rem 3rem;max-width:1600px;}
    [data-testid="stHeader"] {background:transparent;}
    #MainMenu,footer,.stDeployButton,[data-testid="stToolbar"] {display:none;}
    [data-testid="stSidebar"] {background:#17212f;border-right:1px solid #293548;}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] h3 {color:#e6edf6;}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#aab8ca;}
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {gap:.2rem;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label {padding:.52rem .7rem;border-radius:8px;margin:0;width:100%;transition:background .15s;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:#243247;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#f0b429;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {color:#17212f;font-weight:700;}
    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {display:none;}
    [data-testid="stSidebar"] .stButton button {background:#243247;color:#e6edf6;border-color:#3d4c61;}
    [data-testid="stSidebar"] hr {border-color:#354258;}
    h1,h2,h3,h4 {color:var(--ink);letter-spacing:-.025em;}
    .dashboard-header {background:#fff;border:1px solid var(--line);border-left:4px solid #edb52c;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:.5rem;}
    .dashboard-title {font-size:1.4rem!important;font-weight:700;margin:0!important;padding:0!important;color:var(--ink)!important;letter-spacing:-.02em;}
    .dashboard-subtitle {font-family:'DM Sans',sans-serif!important;font-size:.85rem;color:var(--muted);margin:.3rem 0 0;}
    .metric-card,[data-testid="stMetric"] {background:#fff;border:1px solid var(--line);border-radius:12px;padding:1.15rem;box-shadow:0 2px 4px #17212f03;height:100%;}
    .metric-value,[data-testid="stMetricValue"] {font-family:'DM Sans',sans-serif!important;font-size:1.85rem;font-weight:700;line-height:1.25;color:var(--ink)!important;}
    .metric-label {font-size:.73rem;font-weight:600;text-transform:uppercase;letter-spacing:.055em;color:var(--muted);margin:.4rem 0;}
    .metric-change {font-size:.8rem;}.positive {color:#147d61;}.negative {color:#b54708;}
    .section-header {font-size:1.05rem;font-weight:700;color:var(--ink);border-bottom:1px solid var(--line);padding:.5rem 0 .7rem;margin:.7rem 0 1rem;}
    .order-card,.driver-card {background:#fff;border:1px solid var(--line);border-radius:10px;padding:1rem;margin:.6rem 0;}
    .order-id {font-weight:700;color:#8a6200;font-size:.83rem;}.order-customer,.driver-name {font-weight:600;font-size:1rem;color:var(--ink);}
    .order-address,.driver-vehicle,.driver-stat-label {font-size:.8rem;color:var(--muted);}
    .driver-stats {display:flex;gap:1.2rem;margin-top:1rem;}.driver-stat-value {font-weight:700;color:var(--ink);}
    .status-badge {display:inline-block;padding:.2rem .55rem;border-radius:6px;background:#edf1f6;color:#475569;font-size:.72rem;font-weight:600;}
    .status-pending,.status-express {background:#fff3cf;color:#8b6000;}.status-delivered,.status-available {background:#e5f4ec;color:#196c46;}
    .status-in_transit,.status-allocated {background:#e9f0fe;color:#2e55a0;}.status-failed {background:#feecec;color:#ad3535;}
    .stButton button,.stDownloadButton button,.stLinkButton a {border-radius:8px;font-weight:600;}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primaryFormSubmit"] {background:#edb52c;border-color:#edb52c;color:#17212f;}
    [data-testid="stAlert"] {border-radius:9px;border:1px solid #dbe5f0;background:#edf3fa;color:#35516c;}
    [data-testid="stAlert"] p {color:#35516c!important;}
    [data-testid="stExpander"] {background:#fff;border-color:var(--line);border-radius:10px;}
    [data-testid="stSidebar"] [data-testid="stExpander"] {background:#1e2a3b;border-color:#354258;}
    [data-testid="stTabs"] [role="tablist"] {gap:1rem;border-bottom:1px solid var(--line);}
    [data-testid="stTabs"] [role="tab"] {padding:.7rem .2rem;background:transparent;}
    [data-testid="stTabs"] [aria-selected="true"] {color:#8a6200;font-weight:700;}
    [data-baseweb="tab-highlight"] {background:#d99b00;}
    [data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:10px;}
    .tracking-result {background:white;border:1px solid var(--line);border-radius:14px;padding:1.5rem;}
    .timeline-step {flex:1;text-align:center;position:relative;}.timeline-dot {width:16px;height:16px;background:#cbd5e1;border-radius:50%;margin:auto;}
    .timeline-dot.active,.timeline-dot.current {background:#d99b00;}.timeline-line {height:2px;background:#dbe2eb;}.timeline-line.active {background:#d99b00;}
    .timeline-label {font-size:.8rem;margin-top:.5rem;color:var(--muted);}.timeline-label.active {color:var(--ink);}
    @media(max-width:1100px) {[data-testid="stHorizontalBlock"]{flex-wrap:wrap;}[data-testid="stColumn"]{min-width:min(260px,100%);flex:1 1 260px;}}
    @media(max-width:640px) {[data-testid="stMainBlockContainer"]{padding:1rem;}.dashboard-header{padding:1rem;}.dashboard-title{font-size:1.1rem!important;}[data-testid="stColumn"]{min-width:100%;}.metric-card{padding:1rem;} }
    </style>''',unsafe_allow_html=True)
