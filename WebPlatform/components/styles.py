import streamlit as st
import streamlit.components.v1 as components


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

    /* Tracking page */
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
        background: rgba(255,255,255,0.08);
        border: 2px solid rgba(255,255,255,0.15);
        z-index: 2;
        position: relative;
    }

    .timeline-dot.active {
        background: #667eea;
        border-color: #667eea;
        box-shadow: 0 0 16px rgba(102, 126, 234, 0.5);
    }

    .timeline-dot.current {
        animation: pulse 2s infinite;
    }

    .timeline-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: rgba(255,255,255,0.3);
        margin-top: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-align: center;
    }

    .timeline-label.active {
        color: #667eea;
    }

    .timeline-line {
        position: absolute;
        top: 14px;
        right: 50%;
        width: 100%;
        height: 2px;
        background: rgba(255,255,255,0.08);
        z-index: 1;
    }

    .timeline-line.active {
        background: #667eea;
    }

    .tracking-result {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1.5rem;
    }

    .tracking-result:hover {
        border-color: rgba(102, 126, 234, 0.3);
    }

    .tracking-failed {
        border-color: rgba(239, 68, 68, 0.3);
    }

    .tracking-failed:hover {
        border-color: rgba(239, 68, 68, 0.5);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Hide "Deploy" button */
    .stDeployButton {display: none;}

    /* Hide Streamlit header toolbar */
    [data-testid="stToolbar"] {display: none;}

    /* Hide "Made with Streamlit" footer */
    footer:after {
        content: '';
        display: none;
    }

    /* Collapse arrow shown inside the sidebar when it is OPEN — keep it styled */
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
    }

    [data-testid="stSidebarCollapseButton"] button {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 8px !important;
        color: #667eea !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover {
        background: rgba(102, 126, 234, 0.25) !important;
        border-color: rgba(102, 126, 234, 0.7) !important;
        box-shadow: 0 0 12px rgba(102, 126, 234, 0.3) !important;
    }

    [data-testid="stSidebarCollapseButton"] svg {
        fill: #667eea !important;
        color: #667eea !important;
    }
</style>
""", unsafe_allow_html=True)

    # ── Persistent sidebar toggle button ───────────────────────────────────────
    # Strategy: inject a floating button into window.parent.document.body via an
    # invisible iframe.  The button toggles the sidebar using CSS injection
    # (display:none on the sidebar) so we never need to find/click Streamlit's
    # own React-managed buttons — that approach was fragile and produced
    # "zombie" event listeners every time Streamlit recreated the iframe.
    #
    # State is stored in localStorage so it survives Streamlit re-renders.
    # Each iframe instance gets a unique KEY; stale buttons from previous
    # iframe lifecycles are detected by KEY mismatch and replaced with fresh ones.
    components.html("""
<script>
(function () {
    var ID       = 'warex-sidebar-toggle';
    var STYLE_ID = 'warex-sb-override';
    var LS_KEY   = 'warex-sb-collapsed';
    /* Unique per iframe instance — detects zombie buttons from dead iframes */
    var KEY      = Date.now().toString();

    function doc() { return window.parent.document; }

    /* ── State helpers (localStorage) ─────────────────────────────────── */
    function getCollapsed() {
        try { return window.parent.localStorage.getItem(LS_KEY) === '1'; }
        catch(e) { return false; }
    }
    function setCollapsed(v) {
        try { window.parent.localStorage.setItem(LS_KEY, v ? '1' : '0'); }
        catch(e) {}
    }

    /* ── CSS injection — hides/shows the sidebar without touching React ─ */
    function applyStyle() {
        var d  = doc();
        var st = d.getElementById(STYLE_ID);
        if (!st) {
            st    = d.createElement('style');
            st.id = STYLE_ID;
            (d.head || d.body).appendChild(st);
        }
        /* When collapsed: hide sidebar; flexbox/grid will expand main content */
        st.textContent = getCollapsed()
            ? '[data-testid="stSidebar"]{display:none!important}'
            : '';
    }

    /* ── Arrow direction ───────────────────────────────────────────────── */
    function updateArrow() {
        var btn = doc().getElementById(ID);
        if (btn) btn.innerHTML = getCollapsed() ? '&#9654;' : '&#9664;'; /* ▶ / ◀ */
    }

    /* ── Toggle action ─────────────────────────────────────────────────── */
    function toggle() {
        setCollapsed(!getCollapsed());
        applyStyle();
        updateArrow();
    }

    /* ── Button creation / refresh ─────────────────────────────────────── */
    function createBtn() {
        var d   = doc();
        var old = d.getElementById(ID);

        /* Same iframe — just keep CSS and arrow in sync, nothing else needed */
        if (old && old.dataset.frameKey === KEY) {
            applyStyle();
            updateArrow();
            return;
        }

        /* Stale button from a now-dead iframe — its listeners are zombies.
           Remove it so we can rebuild with live closures. */
        if (old) old.remove();

        /* Build a fresh button bound to THIS iframe's closure */
        var btn = d.createElement('button');
        btn.id               = ID;
        btn.dataset.frameKey = KEY;
        btn.title            = 'Toggle sidebar';
        btn.innerHTML        = getCollapsed() ? '&#9654;' : '&#9664;';

        btn.setAttribute('style', [
            'position:fixed',
            'left:0',
            'top:50%',
            'transform:translateY(-50%)',
            'z-index:2147483647',
            'background:linear-gradient(135deg,#1a1a2e,#16213e)',
            'border:1px solid rgba(102,126,234,0.5)',
            'border-left:none',
            'border-radius:0 10px 10px 0',
            'color:#667eea',
            'padding:14px 10px',
            'cursor:pointer',
            'font-size:15px',
            'line-height:1',
            'box-shadow:4px 0 16px rgba(0,0,0,0.4)',
            'transition:all 0.2s ease',
            'outline:none'
        ].join(';'));

        btn.addEventListener('mouseenter', function () {
            this.style.background = 'linear-gradient(135deg,#667eea,#764ba2)';
            this.style.color      = 'white';
            this.style.boxShadow  = '4px 0 24px rgba(102,126,234,0.4)';
        });
        btn.addEventListener('mouseleave', function () {
            this.style.background = 'linear-gradient(135deg,#1a1a2e,#16213e)';
            this.style.color      = '#667eea';
            this.style.boxShadow  = '4px 0 16px rgba(0,0,0,0.4)';
        });
        btn.addEventListener('click', toggle);

        d.body.appendChild(btn);

        /* Re-apply saved CSS state (e.g. sidebar was collapsed before re-render) */
        applyStyle();
        updateArrow();
    }

    /* Staggered retries — Streamlit's React DOM renders asynchronously */
    [100, 400, 900, 2000].forEach(function (ms) { setTimeout(createBtn, ms); });
})();
</script>
""", height=0)
