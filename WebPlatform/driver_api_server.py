"""
Standalone Flask API server for the Sydney Metro Courier driver mobile app.
This runs separately from the Streamlit dashboard.

Usage:
    python driver_api_server.py

The API will be available at http://localhost:5000/api/driver/...
"""

import logging
import os

from flask import Flask
from flask_cors import CORS
from data.data_manager import DataManager
from api.driver_api import create_driver_api

# Configure logging so every [email] line appears in stdout / Railway logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Initialize Flask app
app = Flask(__name__)

# Allow large request bodies (driver photo uploads can be several MB as base64)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Enable CORS for mobile app access
CORS(app, resources={
    r"/api/driver/*": {
        "origins": "*",  # In production, restrict to your mobile app
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize data manager
data_manager = DataManager()

# Register driver API routes
create_driver_api(app, data_manager)

# ── Email configuration check (printed once at startup) ──────────────────────
from utils.email_service import is_email_configured, _get_email_config
_ecfg = _get_email_config(data_manager)
_env_key  = bool(os.environ.get('RESEND_API_KEY', '').strip())
_env_from = os.environ.get('EMAIL_FROM_ADDRESS', '').strip()
print("=" * 60)
print("📧 Email configuration:")
print(f"   RESEND_API_KEY   (env) : {'✅ set' if _env_key else '❌ NOT SET — add this Railway env var'}")
print(f"   EMAIL_FROM_ADDRESS (env): {_env_from or '❌ NOT SET — add this Railway env var'}")
print(f"   resend_api_key   (DB)  : {'✅ set' if data_manager.get_setting('resend_api_key') else '⚠️  not in DB (env var used)'}")
print(f"   email_from_address (DB): {data_manager.get_setting('email_from_address') or '⚠️  not in DB (env var used)'}")
print(f"   email_notifications_enabled (DB): {data_manager.get_setting('email_notifications_enabled', 'false')}")
print(f"   resolved api_key       : {'✅ present' if _ecfg.get('api_key') else '❌ MISSING'}")
print(f"   resolved from_email    : {_ecfg.get('from_email') or '❌ MISSING'}")
print(f"   → Will send emails     : {'✅ YES' if is_email_configured(data_manager) else '❌ NO — fix the items above'}")
print("=" * 60)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'healthy', 'service': 'Sydney Metro Courier Driver API'}, 200

# API documentation endpoint
@app.route('/api/driver/docs', methods=['GET'])
def api_docs():
    """Simple API documentation."""
    return {
        'service': 'Sydney Metro Courier Driver API',
        'version': '1.0.0',
        'endpoints': {
            'POST /api/driver/login': {
                'description': 'Authenticate driver using phone number',
                'body': {'phone': '0412345678'},
                'response': {'token': '...', 'driver': {...}}
            },
            'GET /api/driver/runs': {
                'description': 'Get all runs assigned to driver',
                'headers': {'Authorization': 'Bearer <token>'},
                'response': {'runs': [...], 'total': 5}
            },
            'GET /api/driver/runs/<run_id>/stops': {
                'description': 'Get all stops for a specific run',
                'headers': {'Authorization': 'Bearer <token>'},
                'response': {'stops': [...], 'total': 10}
            },
            'POST /api/driver/stops/<stop_id>/update': {
                'description': 'Update stop status',
                'headers': {'Authorization': 'Bearer <token>'},
                'body': {'status': 'delivered', 'notes': '...'},
                'response': {'success': True}
            },
            'GET /api/driver/profile': {
                'description': 'Get driver profile and stats',
                'headers': {'Authorization': 'Bearer <token>'},
                'response': {'driver': {...}, 'stats': {...}}
            },
            'POST /api/driver/logout': {
                'description': 'Logout and invalidate token',
                'headers': {'Authorization': 'Bearer <token>'},
                'response': {'success': True}
            }
        }
    }, 200


if __name__ == '__main__':
    # Railway provides PORT environment variable
    port = int(os.environ.get('PORT', os.environ.get('API_PORT', 5000)))
    host = os.environ.get('API_HOST', '0.0.0.0')

    # Detect if running on Railway
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') is not None

    print("=" * 60)
    print("🚚 Sydney Metro Courier - Driver API Server")
    print("=" * 60)
    print(f"\n✅ Server starting on http://{host}:{port}")

    if is_production:
        print(f"🌐 Production mode - Railway deployment")
    else:
        print(f"📱 Mobile app can connect to: http://localhost:{port}/api/driver/...")
        print(f"📚 API docs available at: http://localhost:{port}/api/driver/docs")
        print(f"💚 Health check at: http://localhost:{port}/health")

    print("\n" + "=" * 60)
    print("\nPress CTRL+C to stop the server\n")

    # Run Flask app
    app.run(
        host=host,
        port=port,
        debug=not is_production,  # Disable debug in production
        use_reloader=not is_production  # Disable reloader in production
    )
