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
        Get delivery run for the authenticated driver.
        A "run" is simply all orders assigned to that driver.

        Response:
        {
            "runs": [ { ... } ],
            "total": 1
        }
        """
        driver_id = request.driver_id

        # Get all orders for this driver
        orders_df = data_manager.get_orders()

        if orders_df.empty:
            return jsonify({'runs': [], 'total': 0}), 200

        # Get driver name so we can match orders assigned by name OR by ID
        # (web UI stores driver NAME in the driver_id field of orders)
        drivers_df = data_manager.get_drivers()
        driver_match = drivers_df[drivers_df['driver_id'] == driver_id]
        driver_name = driver_match.iloc[0]['name'] if not driver_match.empty else None

        mask = orders_df['driver_id'] == driver_id
        if driver_name:
            mask = mask | (orders_df['driver_id'] == driver_name)
        driver_orders = orders_df[mask]

        if driver_orders.empty:
            return jsonify({'runs': [], 'total': 0}), 200

        # Calculate stats from orders
        total_stops = len(driver_orders)
        completed = len(driver_orders[driver_orders['status'].isin(['delivered', 'completed'])])

        # Determine status
        if completed == 0:
            status = 'Pending'
        elif completed < total_stops:
            status = 'Active'
        else:
            status = 'Completed'

        # Create a single run with all driver's orders
        today = datetime.now().strftime("%Y%m%d")
        run = {
            'id': f'RUN-{driver_id}-{today}',
            'runNumber': f'RUN-{today}',
            'zone': 'Today\'s Deliveries',
            'date': datetime.now().isoformat(),
            'status': status,
            'totalStops': total_stops,
            'completedStops': completed,
            'estimatedDuration': total_stops * 600,  # 10 min per stop
            'totalDistance': total_stops * 2.5,  # 2.5km per stop estimate
        }

        return jsonify({
            'runs': [run],
            'total': 1
        }), 200

    @app.route('/api/driver/runs/<run_id>/stops', methods=['GET'])
    @require_auth
    def get_run_stops(run_id):
        """
        Get all delivery stops (orders) for the driver.
        Run ID is ignored - we just return all orders for this driver.

        Response:
        {
            "stops": [ ... ],
            "total": 10
        }
        """
        driver_id = request.driver_id

        # Get all orders for this driver
        orders_df = data_manager.get_orders()

        if orders_df.empty:
            return jsonify({'stops': [], 'total': 0}), 200

        # Match by driver_id OR driver name (web UI stores name in driver_id field)
        drivers_df = data_manager.get_drivers()
        driver_match = drivers_df[drivers_df['driver_id'] == driver_id]
        driver_name = driver_match.iloc[0]['name'] if not driver_match.empty else None

        mask = orders_df['driver_id'] == driver_id
        if driver_name:
            mask = mask | (orders_df['driver_id'] == driver_name)
        driver_orders = orders_df[mask]

        if driver_orders.empty:
            return jsonify({'stops': [], 'total': 0}), 200

        # Convert to stops format
        stops_list = []
        for idx, (_, order) in enumerate(driver_orders.iterrows(), start=1):
            # Map order status to stop status
            stop_status = 'pending'
            if order['status'] == 'in_transit':
                stop_status = 'inProgress'
            elif order['status'] == 'delivered':
                stop_status = 'delivered'
            elif order['status'] == 'failed':
                stop_status = 'failed'
            elif order['status'] == 'allocated':
                stop_status = 'pending'

            # Get optional fields, convert empty strings to None
            instructions = order.get('instructions', '')
            special_instructions = instructions if instructions else None

            email = order.get('email', '')
            customer_email = email if email else None

            stops_list.append({
                'id': order['order_id'],
                'sequenceNumber': idx,
                'status': stop_status,
                'order': {
                    'id': order['order_id'],
                    'orderNumber': order['order_id'],
                    'customer': {
                        'id': f"C-{idx}",
                        'name': order.get('customer', 'Customer'),
                        'phone': order.get('phone', ''),
                        'email': customer_email
                    },
                    'address': {
                        'street': order.get('address', ''),
                        'suburb': order.get('suburb', ''),
                        'postcode': order.get('postcode', ''),
                        'state': order.get('state', 'NSW'),
                        'latitude': -33.8688,  # TODO: geocode real lat/lng
                        'longitude': 151.2093
                    },
                    'parcels': int(order.get('parcels', 1)),
                    'serviceLevel': order.get('service_level', 'standard'),
                    'specialInstructions': special_instructions,
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
            "notes": "..." (optional),
            "signature": "base64_encoded_image" (optional),
            "photo": "base64_encoded_image" (optional)
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
        signature_base64 = data.get('signature')
        photo_base64 = data.get('photo')

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

        # Prepare update data
        update_data = {'status': backend_status}

        # Record delivery timestamp for completed/failed stops
        if backend_status in ('delivered', 'failed'):
            update_data['delivered_at'] = datetime.now().isoformat()

        # Save signature and photo as base64 data URLs for display
        if signature_base64:
            update_data['signature'] = f"data:image/png;base64,{signature_base64}"

        if photo_base64:
            update_data['photo'] = f"data:image/jpeg;base64,{photo_base64}"

        # Update order status and proof of delivery
        data_manager.update_order(stop_id, **update_data)

        # Send status update email to customer
        from utils.email_service import send_status_update, is_email_configured

        email_sent = False
        if is_email_configured(data_manager):
            # Get fresh order details after update to send email
            orders_df = data_manager.get_orders()
            order_match = orders_df[orders_df['order_id'] == stop_id]

            if not order_match.empty:
                order_data = order_match.iloc[0].to_dict()
                if order_data.get('email'):
                    result = send_status_update(data_manager, order_data, backend_status)
                    email_sent = result.get('success', False)

        return jsonify({
            'success': True,
            'message': f'Stop {stop_id} updated to {new_status}',
            'email_sent': email_sent
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

    @app.route('/api/driver/location', methods=['POST'])
    @require_auth
    def update_driver_location():
        """
        Update driver's current location for real-time tracking.

        Request body:
        {
            "latitude": -33.8688,
            "longitude": 151.2093,
            "timestamp": "2024-01-01T12:00:00Z"
        }

        Response:
        {
            "success": true,
            "message": "Location updated"
        }
        """
        driver_id = request.driver_id
        data = request.get_json()

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        timestamp = data.get('timestamp')

        if latitude is None or longitude is None:
            return jsonify({'error': 'Latitude and longitude are required'}), 400

        # Update driver location in database
        data_manager.update_driver_location(
            driver_id=driver_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp
        )

        return jsonify({
            'success': True,
            'message': 'Location updated'
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
