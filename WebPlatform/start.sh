#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Warex Logistics — Railway startup script
# Patches Streamlit's bundled static files so the correct favicon and OG/social
# meta tags appear in the raw HTML that social media scrapers and link-preview
# generators read (they don't execute JavaScript, so st.set_page_config alone
# is not enough).
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "🔧  Patching Streamlit static files for Warex Logistics branding..."

python3 - <<'PYEOF'
import os, re, shutil

import streamlit as _st
STATIC_DIR = os.path.join(os.path.dirname(_st.__file__), 'static')
APP_DIR    = os.path.dirname(os.path.abspath(__file__))

# ── 1. Replace favicon ────────────────────────────────────────────────────────
logo_src    = os.path.join(APP_DIR, 'static', 'warex_logo.png')
favicon_dst = os.path.join(STATIC_DIR, 'favicon.png')

if os.path.exists(logo_src):
    shutil.copy2(logo_src, favicon_dst)
    print(f"  ✅  Favicon replaced → {favicon_dst}")
else:
    print(f"  ⚠️   Logo not found at {logo_src} — favicon not replaced")

# ── 2. Patch index.html ───────────────────────────────────────────────────────
index_path = os.path.join(STATIC_DIR, 'index.html')

with open(index_path, 'r', encoding='utf-8') as fh:
    html = fh.read()

# Strip any previous patch (safe to re-run on container restart)
html = re.sub(
    r'\s*<!-- WAREX_BRANDING_START -->.*?<!-- WAREX_BRANDING_END -->',
    '',
    html,
    flags=re.DOTALL,
)

# Replace any existing <title> tag
html = re.sub(r'<title>[^<]*</title>', '<title>Warex Logistics</title>', html)

INJECT = """
    <!-- WAREX_BRANDING_START -->
    <title>Warex Logistics</title>
    <meta property="og:title"       content="Warex Logistics" />
    <meta property="og:description" content="Warex Logistics — Courier &amp; Delivery Management Dashboard" />
    <meta property="og:type"        content="website" />
    <meta property="og:site_name"   content="Warex Logistics" />
    <meta name="description"        content="Warex Logistics — Courier &amp; Delivery Management Dashboard" />
    <meta name="application-name"   content="Warex Logistics" />
    <meta name="theme-color"        content="#f59e0b" />
    <meta name="twitter:card"       content="summary" />
    <meta name="twitter:title"      content="Warex Logistics" />
    <meta name="twitter:description" content="Warex Logistics — Courier &amp; Delivery Management Dashboard" />
    <!-- WAREX_BRANDING_END -->"""

# Inject right after the opening <head> tag
html = html.replace('<head>', '<head>' + INJECT, 1)

with open(index_path, 'w', encoding='utf-8') as fh:
    fh.write(html)
print(f"  ✅  index.html patched → {index_path}")
PYEOF

echo "🚀  Starting Streamlit on port ${PORT:-8501}..."
exec streamlit run app.py \
    --server.port "${PORT:-8501}" \
    --server.address 0.0.0.0 \
    --server.headless true
