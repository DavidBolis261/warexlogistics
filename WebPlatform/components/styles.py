import streamlit as st
import streamlit.components.v1 as components

# ── Warex brand palette ───────────────────────────────────────────────────────
# Content bg : #FFFFFF  (white)
# Sidebar    : #0a0a0a  (black — matches logo header/footer)
# Gold       : #F5B800
# Gold deep  : #C89600
# Text       : #1a1a1a  (near-black)
# Subtle     : #6b7280  (secondary text)


def apply_styles(authenticated=False):
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');

    /* ── Hide Streamlit default chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stToolbar"] { display: none; }
    footer:after { content: ''; display: none; }

    /* ── App shell — white content area ── */
    .stApp {
        background: #FFFFFF;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
        background: #FFFFFF;
    }

    /* ── Dark sidebar — matches Warex black branding ── */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0a 0%, #141414 100%) !important;
        border-right: 1px solid rgba(245, 184, 0, 0.15);
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: rgba(255, 255, 255, 0.85) !important;
    }

    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: rgba(255, 255, 255, 0.85) !important;
    }

    [data-testid="stSidebar"] [data-testid="stCaption"] p {
        color: rgba(255, 255, 255, 0.4) !important;
    }

    /* Sidebar radio selected item */
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + div > p {
        color: #F5B800 !important;
        font-weight: 700;
    }

    /* ── Main content text — dark on white ── */
    .main p, .main span, .main div, .main label {
        color: #1a1a1a;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a !important;
    }

    /* Streamlit auto-generated paragraph text */
    .stMarkdown p { color: #1a1a1a !important; }
    .stText       { color: #1a1a1a !important; }

    /* ── Metric widgets ── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    [data-testid="stMetricValue"] > div {
        color: #F5B800 !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] > div {
        color: #6b7280 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ── Dashboard header strip ── */
    .dashboard-header {
        background: linear-gradient(90deg, #F5B800 0%, #C89600 100%);
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
        color: #0a0a0a;
        margin: 0;
    }

    .dashboard-subtitle {
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        color: rgba(0,0,0,0.6);
        margin-top: 0.25rem;
    }

    /* ── Metric card (custom HTML) ── */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.07);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(245, 184, 0, 0.4);
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }

    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: #F5B800;
        line-height: 1;
    }

    .metric-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        color: #6b7280;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-change.positive { color: #10b981; }
    .metric-change.negative { color: #ef4444; }

    /* ── Status badges ── */
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

    .status-pending    { background: #F5B800; color: #0a0a0a; }
    .status-in-transit { background: #3b82f6; color: white; }
    .status-delivered  { background: #10b981; color: white; }
    .status-failed     { background: #ef4444; color: white; }
    .status-available  { background: #10b981; color: white; }
    .status-on-route   { background: #3b82f6; color: white; }
    .status-offline    { background: #e5e7eb; color: #6b7280; }

    /* ── DataFrames ── */
    .dataframe {
        font-family: 'DM Sans', sans-serif !important;
        background: #FFFFFF !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        border-radius: 8px !important;
    }

    .dataframe th {
        background: rgba(245, 184, 0, 0.12) !important;
        color: #1a1a1a !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 1px !important;
        padding: 1rem !important;
    }

    .dataframe td {
        color: #1a1a1a !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid rgba(0,0,0,0.05) !important;
    }

    /* ── Section header ── */
    .section-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(245, 184, 0, 0.4);
    }

    /* ── Order cards ── */
    .order-card {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.07);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }

    .order-card:hover {
        border-color: rgba(245, 184, 0, 0.35);
        box-shadow: 0 4px 16px rgba(245, 184, 0, 0.1);
    }

    .order-id {
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        color: #F5B800;
        font-weight: 700;
    }

    .order-customer {
        font-family: 'DM Sans', sans-serif;
        font-size: 1rem;
        color: #1a1a1a;
        margin-top: 0.5rem;
    }

    .order-address {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    /* ── Driver cards ── */
    .driver-card {
        background: linear-gradient(135deg, rgba(245, 184, 0, 0.05) 0%, rgba(200, 150, 0, 0.02) 100%);
        border: 1px solid rgba(245, 184, 0, 0.18);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .driver-name   { font-family: 'DM Sans', sans-serif; font-size: 1.1rem; font-weight: 700; color: #1a1a1a; }
    .driver-vehicle{ font-family: 'Space Mono', monospace; font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem; }
    .driver-stats  { display: flex; gap: 1.5rem; margin-top: 1rem; }
    .driver-stat   { text-align: center; }

    .driver-stat-value {
        font-family: 'Space Mono', monospace;
        font-size: 1.25rem;
        font-weight: 700;
        color: #F5B800;
    }

    .driver-stat-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.7rem;
        color: #9ca3af;
        text-transform: uppercase;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
        color: #1a1a1a;
        border: 1px solid rgba(0,0,0,0.12);
        background: #FFFFFF;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(245, 184, 0, 0.25);
        border-color: rgba(245, 184, 0, 0.5);
    }

    /* Primary buttons — gold fill with black text */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(90deg, #F5B800, #C89600) !important;
        color: #0a0a0a !important;
        border: none !important;
        font-weight: 700 !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        box-shadow: 0 4px 18px rgba(245, 184, 0, 0.45) !important;
    }

    /* ── Input fields ── */
    .stTextInput input,
    .stTextArea textarea {
        background: #FFFFFF !important;
        color: #1a1a1a !important;
        border: 1px solid rgba(0,0,0,0.15) !important;
        border-radius: 8px !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #F5B800 !important;
        box-shadow: 0 0 0 3px rgba(245, 184, 0, 0.15) !important;
    }

    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stNumberInput label, .stDateInput label {
        color: #1a1a1a !important;
        font-weight: 600;
    }

    /* Selectbox */
    [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border: 1px solid rgba(0,0,0,0.15) !important;
        color: #1a1a1a !important;
    }

    [data-baseweb="select"] span { color: #1a1a1a !important; }

    /* Select dropdown options */
    [role="listbox"] li {
        background: #FFFFFF !important;
        color: #1a1a1a !important;
    }

    [role="option"]:hover,
    [role="option"][aria-selected="true"] {
        background: rgba(245, 184, 0, 0.12) !important;
        color: #1a1a1a !important;
    }

    /* Number input */
    .stNumberInput input {
        background: #FFFFFF !important;
        color: #1a1a1a !important;
        border: 1px solid rgba(0,0,0,0.15) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: #F5F5F5;
        padding: 0.4rem;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        color: #6b7280;
        border-radius: 8px;
        padding: 0.65rem 1.4rem;
        background: transparent;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #F5B800 0%, #C89600 100%) !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        color: #1a1a1a !important;
        background: #F9F9F9 !important;
        border-radius: 8px !important;
        border: 1px solid rgba(0,0,0,0.08) !important;
    }

    /* ── Checkbox / radio ── */
    .stCheckbox label, .stRadio label { color: #1a1a1a !important; }

    /* ── Info / warning / error / success boxes ── */
    .stAlert {
        border-radius: 10px !important;
    }

    /* ── Live indicator ── */
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
        50%       { opacity: 0.5; transform: scale(1.2); }
    }

    /* ── Priority borders ── */
    .priority-express  { border-left: 4px solid #ef4444; }
    .priority-standard { border-left: 4px solid #F5B800; }
    .priority-economy  { border-left: 4px solid #d1d5db; }

    /* ── Toast ── */
    .toast {
        position: fixed;
        top: 1rem;
        right: 1rem;
        background: linear-gradient(90deg, #F5B800 0%, #C89600 100%);
        color: #0a0a0a;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to   { transform: translateX(0);    opacity: 1; }
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar       { width: 7px; height: 7px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; }
    ::-webkit-scrollbar-thumb { background: rgba(245,184,0,0.35); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(245,184,0,0.6); }

    /* ── Tracking page ── */
    .tracking-timeline {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        margin: 1.5rem 0 2rem;
        padding: 0 1rem;
    }

    .timeline-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
        max-width: 150px;
    }

    .timeline-dot {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: rgba(0,0,0,0.06);
        border: 2px solid rgba(0,0,0,0.12);
        z-index: 2;
        position: relative;
    }

    .timeline-dot.active {
        background: #F5B800;
        border-color: #F5B800;
        box-shadow: 0 0 14px rgba(245, 184, 0, 0.45);
    }

    .timeline-dot.current { animation: pulse 2s infinite; }

    .timeline-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: #9ca3af;
        margin-top: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-align: center;
    }

    .timeline-label.active { color: #C89600; }

    .timeline-line {
        position: absolute;
        top: 14px;
        right: 50%;
        width: 100%;
        height: 2px;
        background: rgba(0,0,0,0.08);
        z-index: 1;
    }

    .timeline-line.active { background: #F5B800; }

    .tracking-result {
        background: #FFFFFF;
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }

    .tracking-result:hover { border-color: rgba(245, 184, 0, 0.3); }
    .tracking-failed       { border-color: rgba(239, 68, 68, 0.3); }
    .tracking-failed:hover { border-color: rgba(239, 68, 68, 0.5); }

    /* ── Sidebar collapse button ── */
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
    }

    [data-testid="stSidebarCollapseButton"] button {
        background: rgba(245, 184, 0, 0.1) !important;
        border: 1px solid rgba(245, 184, 0, 0.35) !important;
        border-radius: 8px !important;
        color: #F5B800 !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover {
        background: rgba(245, 184, 0, 0.22) !important;
        border-color: rgba(245, 184, 0, 0.7) !important;
    }

    [data-testid="stSidebarCollapseButton"] svg {
        fill: #F5B800 !important;
        color: #F5B800 !important;
    }
</style>
""", unsafe_allow_html=True)

    if not authenticated:
        return

    # ── Persistent sidebar toggle button ───────────────────────────────────────
    components.html("""
<script>
(function () {
    var ID  = 'warex-sidebar-toggle';
    var KEY = Date.now().toString();

    function doc()     { return window.parent.document; }
    function sidebar() { return doc().querySelector('[data-testid="stSidebar"]'); }

    function isOpen() {
        var sb = sidebar();
        return !sb || sb.getAttribute('aria-expanded') !== 'false';
    }

    function updateArrow() {
        var btn = doc().getElementById(ID);
        if (btn) btn.innerHTML = isOpen() ? '&#9664;' : '&#9654;';
    }

    function toggle() {
        var d    = doc();
        var open = isOpen();
        var el;

        if (open) {
            el = d.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
                 d.querySelector('[data-testid="stSidebarCollapseButton"]');
            if (el) el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        } else {
            el = d.querySelector('[data-testid="stExpandSidebarButton"]') ||
                 d.querySelector('[data-testid="stExpandSidebarButton"] button');
            if (el) el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        }

        setTimeout(updateArrow, 350);
        setTimeout(updateArrow, 750);
    }

    function createBtn() {
        var d   = doc();
        var old = d.getElementById(ID);

        if (old && old.dataset.frameKey === KEY) { updateArrow(); return; }
        if (old) old.remove();

        var staleStyle = d.getElementById('warex-sb-override');
        if (staleStyle) staleStyle.remove();

        var btn = d.createElement('button');
        btn.id               = ID;
        btn.dataset.frameKey = KEY;
        btn.title            = 'Toggle sidebar';
        btn.innerHTML        = isOpen() ? '&#9664;' : '&#9654;';

        btn.setAttribute('style', [
            'position:fixed',
            'left:0',
            'top:50%',
            'transform:translateY(-50%)',
            'z-index:2147483647',
            'background:linear-gradient(135deg,#141414,#1c1c1c)',
            'border:1px solid rgba(245,184,0,0.45)',
            'border-left:none',
            'border-radius:0 10px 10px 0',
            'color:#F5B800',
            'padding:14px 10px',
            'cursor:pointer',
            'font-size:15px',
            'line-height:1',
            'box-shadow:4px 0 16px rgba(0,0,0,0.15)',
            'transition:all 0.2s ease',
            'outline:none'
        ].join(';'));

        btn.addEventListener('mouseenter', function () {
            this.style.background = 'linear-gradient(135deg,#F5B800,#C89600)';
            this.style.color      = '#0a0a0a';
            this.style.boxShadow  = '4px 0 20px rgba(245,184,0,0.35)';
        });
        btn.addEventListener('mouseleave', function () {
            this.style.background = 'linear-gradient(135deg,#141414,#1c1c1c)';
            this.style.color      = '#F5B800';
            this.style.boxShadow  = '4px 0 16px rgba(0,0,0,0.15)';
        });
        btn.addEventListener('click', toggle);

        d.body.appendChild(btn);
        updateArrow();

        var sb = sidebar();
        if (sb) {
            new MutationObserver(updateArrow)
                .observe(sb, {attributes: true, attributeFilter: ['aria-expanded']});
        }
    }

    [100, 400, 900, 2000].forEach(function (ms) { setTimeout(createBtn, ms); });
})();
</script>
""", height=0)
