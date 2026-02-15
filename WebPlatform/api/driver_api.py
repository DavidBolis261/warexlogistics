"""
REST API endpoints for the Sydney Metro Courier driver mobile app.
Provides authentication and data access for drivers.
"""

from flask import Flask, request, jsonify
from functools import wraps
import secrets
from datetime import datetime, timedelta
import pandas as pd

# Simple token storage (in production, use Redis or database)
_active_tokens = {}


def create_driver_api(app: Flask, data_manager):
    """Register driver API routes with the Flask app."""

    def require_auth(f):
        """Decorator to require valid authentication token."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')

            if not token or token not in _active_tokens:
                return jsonify({'error': 'Unauthorized', 'message': 'Invalid or missing token'}), 401

            # Check token expiration
            token_data = _active_tokens[token]
            if datetime.fromisoformat(token_data['expires']) < datetime.now():
                del _active_tokens[token]
                return jsonify({'error': 'Unauthorized', 'message': 'Token expired'}), 401

            # Add driver info to request context
            request.driver_id = token_data['driver_id']
            request.driver_phone = token_data['phone']

            return f(*args, **kwargs)
        return decorated_function

    @app.route('/api/driver/login', methods=['POST'])
    def driver_login():
        """
        Authenticate driver using phone number (their driver ID).

        Request body:
        {
            "phone": "0412345678"
        }

        Response:
        {
            "success": true,
            "token": "...",
            "driver": { ... },
            "expires_at": "2024-01-01T12:00:00"
        }
        """
        data = request.get_json()
        phone = data.get('phone', '').strip()

        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400

        # Get all drivers
        drivers_df = data_manager.get_drivers()

        if drivers_df.empty:
            return jsonify({'error': 'No drivers found'}), 404

        # Find driver by phone number
        driver_match = drivers_df[drivers_df['phone'] == phone]

        if driver_match.empty:
            return jsonify({'error': 'Driver not found', 'message': 'No driver with this phone number'}), 404

        driver = driver_match.iloc[0].to_dict()

        # Generate auth token (valid for 30 days)
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(days=30)

        _active_tokens[token] = {
            'driver_id': driver['driver_id'],
            'phone': driver['phone'],
            'expires': expires.isoformat()
        }

        # Format driver response
        driver_response = {
            'id': driver['driver_id'],
            'name': driver['name'],
            'phone': driver['phone'],
            'vehicleType': driver['vehicle_type'],
            'plateNumber': driver.get('plate', ''),
            'rating': float(driver.get('rating', 4.5)),
            'totalDeliveries': int(driver.get('deliveries_today', 0)),
            'successRate': float(driver.get('success_rate', 0.95)),
            'status': driver.get('status', 'available'),
            'currentZone': driver.get('current_zone', '')
        }

        return jsonify({
            'success': True,
            'token': token,
            'driver': driver_response,
            'expires_at': expires.isoformat()
        }), 200

    @app.route('/api/driver/runs', methods=['GET'])
    @require_auth
    def get_driver_runs():
        """
        Get all delivery runs assigned to the authenticated driver.

        Query params:
        - status: filter by status (active, pending, completed)
        - date: filter by date (YYYY-MM-DD)

        Response:
        {
            "runs": [ ... ],
            "total": 5
        }
        """
        driver_id = request.driver_id

        # Get all runs
        runs_df = data_manager.get_runs()

        if runs_df.empty:
            return jsonify({'runs': [], 'total': 0}), 200

        # Filter by driver
        driver_runs = runs_df[runs_df['driver_id'] == driver_id]

        # Apply filters
        status_filter = request.args.get('status')
        if status_filter and 'status' in driver_runs.columns:
            driver_runs = driver_runs[driver_runs['status'] == status_filter]

        # Convert to list of dicts
        runs_list = []
        for _, run in driver_runs.iterrows():
            # Get orders for this run
            orders_df = data_manager.get_orders()
            run_orders = orders_df[
                (orders_df['driver_id'] == driver_id) &
                (orders_df['status'].isin(['allocated', 'in_transit', 'delivered']))
            ] if not orders_df.empty else pd.DataFrame()

            runs_list.append({
                'id': run['run_id'],
                'runNumber': run['run_id'],
                'zone': run.get('zone', ''),
                'date': run.get('created_at', datetime.now().isoformat()),
                'status': run.get('status', 'pending'),
                'totalStops': int(run.get('total_stops', 0)),
                'completedStops': int(run.get('completed', 0)),
                'estimatedDuration': 7200,  # Default 2 hours
                'totalDistance': 15.5,  # Default distance
            })

        return jsonify({
            'runs': runs_list,
            'total': len(runs_list)
        }), 200

    @app.route('/api/driver/runs/<run_id>/stops', methods=['GET'])
    @require_auth
    def get_run_stops(run_id):
        """
        Get all delivery stops for a specific run.

        Response:
        {
            "stops": [ ... ],
            "total": 10
        }
        """
        driver_id = request.driver_id

        # Verify run belongs to driver
        runs_df = data_manager.get_runs()
        if runs_df.empty:
            return jsonify({'error': 'Run not found'}), 404

        run = runs_df[runs_df['run_id'] == run_id]
        if run.empty:
            return jsonify({'error': 'Run not found'}), 404

        if run.iloc[0]['driver_id'] != driver_id:
            return jsonify({'error': 'Unauthorized', 'message': 'This run is not assigned to you'}), 403

        # Get orders for this run
        orders_df = data_manager.get_orders()
        run_orders = orders_df[
            (orders_df['driver_id'] == driver_id) &
            (orders_df['status'].isin(['allocated', 'in_transit', 'delivered', 'failed']))
        ] if not orders_df.empty else pd.DataFrame()

        # Convert to stops format
        stops_list = []
        for idx, order in run_orders.iterrows():
            stop_status = 'pending'
            if order['status'] == 'in_transit':
                stop_status = 'inProgress'
            elif order['status'] == 'delivered':
                stop_status = 'delivered'
            elif order['status'] == 'failed':
                stop_status = 'failed'

            stops_list.append({
                'id': order['order_id'],
                'sequenceNumber': idx + 1,
                'status': stop_status,
                'order': {
                    'id': order['order_id'],
                    'orderNumber': order['order_id'],
                    'customer': {
                        'id': f"C-{idx}",
                        'name': order.get('customer', 'Customer'),
                        'phone': order.get('phone', ''),
                        'email': order.get('email', '')
                    },
                    'address': {
                        'street': order.get('address', ''),
                        'suburb': order.get('suburb', ''),
                        'postcode': order.get('postcode', ''),
                        'state': order.get('state', 'NSW'),
                        'latitude': -33.8688,
                        'longitude': 151.2093
                    },
                    'parcels': int(order.get('parcels', 1)),
                    'serviceLevel': order.get('service_level', 'standard'),
                    'specialInstructions': order.get('instructions', ''),
                    'createdAt': order.get('created_at', datetime.now().isoformat())
                }
            })

        return jsonify({
            'stops': stops_list,
            'total': len(stops_list)
        }), 200

    @app.route('/api/driver/stops/<stop_id>/update', methods=['POST'])
    @require_auth
    def update_stop_status(stop_id):
        """
        Update the status of a delivery stop.

        Request body:
        {
            "status": "delivered" | "failed" | "inProgress",
            "failureReason": "notHome" (optional, required if status is failed),
            "notes": "..." (optional)
        }

        Response:
        {
            "success": true,
            "stop": { ... }
        }
        """
        driver_id = request.driver_id
        data = request.get_json()

        new_status = data.get('status')
        failure_reason = data.get('failureReason')
        notes = data.get('notes', '')

        if not new_status:
            return jsonify({'error': 'Status is required'}), 400

        # Map mobile statuses to backend statuses
        status_map = {
            'pending': 'allocated',
            'inProgress': 'in_transit',
            'delivered': 'delivered',
            'failed': 'failed'
        }

        backend_status = status_map.get(new_status, 'allocated')

        # Update order status
        data_manager.update_order(stop_id, status=backend_status)

        return jsonify({
            'success': True,
            'message': f'Stop {stop_id} updated to {new_status}'
        }), 200

    @app.route('/api/driver/profile', methods=['GET'])
    @require_auth
    def get_driver_profile():
        """
        Get the authenticated driver's profile information.

        Response:
        {
            "driver": { ... },
            "stats": { ... }
        }
        """
        driver_id = request.driver_id

        # Get driver info
        drivers_df = data_manager.get_drivers()
        driver_match = drivers_df[drivers_df['driver_id'] == driver_id]

        if driver_match.empty:
            return jsonify({'error': 'Driver not found'}), 404

        driver = driver_match.iloc[0].to_dict()

        # Get driver stats
        orders_df = data_manager.get_orders()
        driver_orders = orders_df[orders_df['driver_id'] == driver_id] if not orders_df.empty else pd.DataFrame()

        today = datetime.now().strftime('%Y-%m-%d')
        deliveries_today = len(driver_orders[
            (driver_orders['status'] == 'delivered') &
            (driver_orders['order_date'] == today)
        ]) if not driver_orders.empty else 0

        total_delivered = len(driver_orders[driver_orders['status'] == 'delivered']) if not driver_orders.empty else 0

        return jsonify({
            'driver': {
                'id': driver['driver_id'],
                'name': driver['name'],
                'phone': driver['phone'],
                'vehicleType': driver['vehicle_type'],
                'plateNumber': driver.get('plate', ''),
                'rating': float(driver.get('rating', 4.5)),
                'status': driver.get('status', 'available'),
                'currentZone': driver.get('current_zone', '')
            },
            'stats': {
                'deliveriesToday': deliveries_today,
                'totalDeliveries': total_delivered,
                'successRate': float(driver.get('success_rate', 0.95)),
                'activeOrders': int(driver.get('active_orders', 0))
            }
        }), 200

    @app.route('/api/driver/logout', methods=['POST'])
    @require_auth
    def driver_logout():
        """Logout and invalidate the current token."""
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if token in _active_tokens:
            del _active_tokens[token]

        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

    return app
