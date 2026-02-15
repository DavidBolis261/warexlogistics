"""
Standalone Flask API server for the Sydney Metro Courier driver mobile app.
This runs separately from the Streamlit dashboard.

Usage:
    python driver_api_server.py

The API will be available at http://localhost:5000/api/driver/...
"""

from flask import Flask
from flask_cors import CORS
from data.data_manager import DataManager
from api.driver_api import create_driver_api
import os

# Initialize Flask app
app = Flask(__name__)

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
    port = int(os.environ.get('API_PORT', 5000))
    host = os.environ.get('API_HOST', '0.0.0.0')

    print("=" * 60)
    print("🚚 Sydney Metro Courier - Driver API Server")
    print("=" * 60)
    print(f"\n✅ Server starting on http://{host}:{port}")
    print(f"📱 Mobile app can connect to: http://localhost:{port}/api/driver/...")
    print(f"📚 API docs available at: http://localhost:{port}/api/driver/docs")
    print(f"💚 Health check at: http://localhost:{port}/health\n")
    print("=" * 60)
    print("\nPress CTRL+C to stop the server\n")

    # Run Flask app
    app.run(
        host=host,
        port=port,
        debug=True,
        use_reloader=True
    )
