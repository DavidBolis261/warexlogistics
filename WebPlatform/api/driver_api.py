"""
REST API endpoints for the Sydney Metro Courier driver mobile app.
Provides authentication and data access for drivers.
"""

from flask import Flask, request, jsonify
from functools import wraps
import secrets
from datetime import datetime, timedelta
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def create_driver_api(app: Flask, data_manager):
    """Register driver API routes with the Flask app."""

    # ── Token helpers ─────────────────────────────────────────────────────────

    def _save_token(token, driver_id, phone, expires_at: datetime):
        """Persist a driver token. Works with both Postgres and SQLite stores."""
        store = data_manager.store
        if hasattr(store, 'save_driver_token'):
            store.save_driver_token(token, driver_id, phone, expires_at.isoformat())
        # Legacy fallback: keep an in-memory copy for the lifetime of this process
        _mem_tokens[token] = {
            'driver_id': driver_id,
            'phone': phone,
            'expires': expires_at.isoformat(),
        }

    def _get_token(token):
        """Look up a token — DB first, then in-memory cache."""
        store = data_manager.store
        if hasattr(store, 'get_driver_token'):
            row = store.get_driver_token(token)
            if row:
                # Refresh memory cache
                _mem_tokens[token] = row
                return row
        # Fallback to in-memory (dev/legacy)
        return _mem_tokens.get(token)

    def _delete_token(token):
        store = data_manager.store
        if hasattr(store, 'delete_driver_token'):
            store.delete_driver_token(token)
        _mem_tokens.pop(token, None)

    # In-memory cache — used as a fast-path and fallback when store doesn't
    # have driver_token methods (e.g. old schema).
    _mem_tokens = {}

    # ── Auth decorator ────────────────────────────────────────────────────────

    def require_auth(f):
        """Decorator to require valid authentication token."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')

            if not token:
                return jsonify({'error': 'Unauthorized', 'message': 'Missing token'}), 401

            token_data = _get_token(token)
            if not token_data:
                return jsonify({'error': 'Unauthorized', 'message': 'Invalid or expired token'}), 401

            # Check expiration
            try:
                expires = datetime.fromisoformat(str(token_data['expires']))
                if expires < datetime.now():
                    _delete_token(token)
                    return jsonify({'error': 'Unauthorized', 'message': 'Token expired'}), 401
            except (ValueError, KeyError):
                _delete_token(token)
                return jsonify({'error': 'Unauthorized', 'message': 'Invalid token data'}), 401

            request.driver_id = token_data['driver_id']
            request.driver_phone = token_data['phone']
            return f(*args, **kwargs)
        return decorated_function

    # ── Login ─────────────────────────────────────────────────────────────────

    @app.route('/api/driver/login', methods=['POST'])
    def driver_login():
        """
        Authenticate driver using phone number (their driver ID).

        Request body:
        {
            "phone": "0412345678"
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

        _save_token(token, driver['driver_id'], driver['phone'], expires)

        # Purge stale tokens periodically (on every login)
        try:
            if hasattr(data_manager.store, 'purge_expired_driver_tokens'):
                data_manager.store.purge_expired_driver_tokens()
        except Exception:
            pass

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

    # ── Runs ──────────────────────────────────────────────────────────────────

    @app.route('/api/driver/runs', methods=['GET'])
    @require_auth
    def get_driver_runs():
        """Get delivery run for the authenticated driver."""
        driver_id = request.driver_id

        orders_df = data_manager.get_orders()

        if orders_df.empty:
            return jsonify({'runs': [], 'total': 0}), 200

        driver_orders = orders_df[orders_df['driver_id'] == driver_id]

        if driver_orders.empty:
            return jsonify({'runs': [], 'total': 0}), 200

        total_stops = len(driver_orders)
        completed = len(driver_orders[driver_orders['status'].isin(['delivered', 'completed'])])

        if completed == 0:
            status = 'Pending'
        elif completed < total_stops:
            status = 'Active'
        else:
            status = 'Completed'

        today = datetime.now().strftime("%Y%m%d")
        run = {
            'id': f'RUN-{driver_id}-{today}',
            'runNumber': f'RUN-{today}',
            'zone': "Today's Deliveries",
            'date': datetime.now().isoformat(),
            'status': status,
            'totalStops': total_stops,
            'completedStops': completed,
            'estimatedDuration': total_stops * 600,
            'totalDistance': total_stops * 2.5,
        }

        return jsonify({'runs': [run], 'total': 1}), 200

    # ── Stops ─────────────────────────────────────────────────────────────────

    @app.route('/api/driver/runs/<run_id>/stops', methods=['GET'])
    @require_auth
    def get_run_stops(run_id):
        """Get all delivery stops (orders) for the driver."""
        driver_id = request.driver_id

        orders_df = data_manager.get_orders()

        if orders_df.empty:
            return jsonify({'stops': [], 'total': 0}), 200

        driver_orders = orders_df[orders_df['driver_id'] == driver_id]

        if driver_orders.empty:
            return jsonify({'stops': [], 'total': 0}), 200

        # Map backend statuses to mobile app stop statuses (vectorized)
        status_map = {'in_transit': 'inProgress', 'delivered': 'delivered', 'failed': 'failed'}
        driver_orders = driver_orders.reset_index(drop=True)
        driver_orders['stop_status'] = driver_orders['status'].map(status_map).fillna('pending')

        stops_list = [
            {
                'id': row['order_id'],
                'sequenceNumber': seq,
                'status': row['stop_status'],
                'order': {
                    'id': row['order_id'],
                    'orderNumber': row['order_id'],
                    'customer': {
                        'id': f"C-{seq}",
                        'name': row.get('customer') or 'Customer',
                        'phone': row.get('phone') or '',
                        'email': row.get('email') or '',
                    },
                    'address': {
                        'street': row.get('address') or '',
                        'suburb': row.get('suburb') or '',
                        'postcode': row.get('postcode') or '',
                        'state': row.get('state') or 'NSW',
                        'latitude': -33.8688,
                        'longitude': 151.2093,
                    },
                    'parcels': int(row.get('parcels') or 1),
                    'serviceLevel': row.get('service_level') or 'standard',
                    'specialInstructions': row.get('special_instructions') or '',
                    'createdAt': row.get('created_at') or datetime.now().isoformat(),
                },
            }
            for seq, row in enumerate(driver_orders.to_dict('records'), start=1)
        ]

        return jsonify({'stops': stops_list, 'total': len(stops_list)}), 200

    # ── Stop update (status + optional media) ─────────────────────────────────

    @app.route('/api/driver/stops/<stop_id>/update', methods=['POST'])
    @require_auth
    def update_stop_status(stop_id):
        """
        Update the status and/or proof-of-delivery media for a stop.

        Both `status` and media fields are optional independently:
        - Status-only call: { "status": "delivered", "notes": "..." }
        - Media-only call:  { "photo": "<base64>", "signature": "<base64>" }
        - Combined call:    { "status": "delivered", "photo": "<base64>", ... }

        At least one of status or media must be present.
        """
        data = request.get_json() or {}

        new_status = data.get('status')
        failure_reason = data.get('failureReason')
        notes = data.get('notes', '')
        photo_b64 = data.get('photo')
        signature_b64 = data.get('signature')

        has_status = bool(new_status)
        has_media = bool(photo_b64 or signature_b64)

        if not has_status and not has_media:
            return jsonify({'error': 'At least one of status or media must be provided'}), 400

        update_fields = {}

        if has_status:
            # Map mobile statuses to backend statuses
            status_map = {
                'pending': 'allocated',
                'inProgress': 'in_transit',
                'delivered': 'delivered',
                'failed': 'failed',
            }
            backend_status = status_map.get(new_status, 'allocated')
            update_fields['status'] = backend_status
            if notes:
                update_fields['delivery_notes'] = notes

        if has_media:
            if photo_b64:
                update_fields['proof_photo'] = photo_b64
            if signature_b64:
                update_fields['proof_signature'] = signature_b64

        try:
            data_manager.update_order(stop_id, **update_fields)
        except Exception as exc:
            logger.error(f"update_stop_status error for {stop_id}: {exc}", exc_info=True)
            return jsonify({'error': 'Failed to update stop', 'detail': str(exc)}), 500

        logger.info(
            f"[stop] {stop_id} updated — status={new_status or '(none)'} "
            f"photo={'yes' if photo_b64 else 'no'} sig={'yes' if signature_b64 else 'no'}"
        )

        return jsonify({
            'success': True,
            'message': f'Stop {stop_id} updated',
        }), 200

    # ── Profile ───────────────────────────────────────────────────────────────

    @app.route('/api/driver/profile', methods=['GET'])
    @require_auth
    def get_driver_profile():
        """Get the authenticated driver's profile information."""
        driver_id = request.driver_id

        drivers_df = data_manager.get_drivers()
        driver_match = drivers_df[drivers_df['driver_id'] == driver_id]

        if driver_match.empty:
            return jsonify({'error': 'Driver not found'}), 404

        driver = driver_match.iloc[0].to_dict()

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

    # ── Explicit email trigger (called by iOS app after delivery) ─────────────

    @app.route('/api/driver/stops/<stop_id>/notify', methods=['POST'])
    @require_auth
    def notify_customer(stop_id):
        """
        Explicitly trigger a customer notification email for a stop.
        The iOS app calls this right after a successful status update so the
        email send is visible in logs and can be retried independently.

        Request body: { "status": "delivered" }  (optional — defaults to 'delivered')
        """
        from utils.email_service import send_status_update, is_email_configured

        data = request.get_json() or {}
        new_status = data.get('status', 'delivered')

        if not is_email_configured(data_manager):
            logger.warning(f"[email/notify] email not configured for stop {stop_id}")
            return jsonify({
                'success': False,
                'error': 'Email not configured on server',
            }), 200  # 200 so iOS doesn't show an error toast

        try:
            order = data_manager.store.get_order_by_id(stop_id)
            if not order:
                logger.warning(f"[email/notify] order {stop_id} not found")
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            order_dict = dict(order)
            to_email = order_dict.get('email', '')
            if not to_email:
                logger.warning(f"[email/notify] no customer email for order {stop_id}")
                return jsonify({'success': False, 'error': 'No customer email'}), 200

            logger.info(f"[email/notify] sending '{new_status}' email to {to_email} for order {stop_id}")
            result = send_status_update(data_manager, order_dict, new_status)

            if result.get('success'):
                logger.info(f"[email/notify] ✅ sent to {to_email}")
                return jsonify({'success': True}), 200
            else:
                logger.warning(f"[email/notify] ❌ failed: {result.get('error')}")
                return jsonify({'success': False, 'error': result.get('error')}), 200

        except Exception as exc:
            logger.error(f"[email/notify] exception for {stop_id}: {exc}", exc_info=True)
            return jsonify({'success': False, 'error': str(exc)}), 500

    # ── Logout ────────────────────────────────────────────────────────────────

    @app.route('/api/driver/logout', methods=['POST'])
    @require_auth
    def driver_logout():
        """Logout and invalidate the current token."""
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        _delete_token(token)
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

    return app
