"""
External Partner API — allows third-party companies to submit orders
and check order status via a simple REST API.

Authentication: pass your API key in the X-API-Key header on every request.

Endpoints:
  POST /api/v1/orders                        — create a new order
  GET  /api/v1/orders/<tracking_number>      — get order status
  GET  /api/v1/orders/<tracking_number>/track — full tracking timeline
"""

import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# ── API key ───────────────────────────────────────────────────────────────────
# Set EXTERNAL_API_KEY in Railway env vars.  The hardcoded fallback is used in
# development only — change it before giving a key to any external partner.
_EXTERNAL_API_KEY = os.environ.get('EXTERNAL_API_KEY', 'WAREX-PARTNER-KEY-2026')


def _require_api_key(f):
    """Decorator — rejects requests that don't carry the correct API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key', '').strip()
        if not key:
            return jsonify({
                'success': False,
                'error': 'Missing API key',
                'hint': 'Pass your key in the X-API-Key header',
            }), 401
        if key != _EXTERNAL_API_KEY:
            logger.warning(f"[external-api] Invalid API key attempt from {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Invalid API key'}), 403
        return f(*args, **kwargs)
    return decorated


def create_external_api(app, data_manager):
    """Register all external partner API routes."""

    # ── POST /api/v1/orders ───────────────────────────────────────────────────
    @app.route('/api/v1/orders', methods=['POST'])
    @_require_api_key
    def external_create_order():
        """
        Create a new delivery order.

        Headers:
            X-API-Key: <your api key>
            Content-Type: application/json

        Body (all fields marked * are required):
        {
            "customer_name":  "Jane Smith",          *
            "email":          "jane@example.com",    *
            "phone":          "0412345678",           *
            "address":        "123 George St",        *
            "suburb":         "Sydney",               *
            "state":          "NSW",
            "postcode":       "2000",                 *
            "parcels":        1,
            "service_level":  "standard",             (standard / express / economy)
            "instructions":   "Leave at door",
            "company":        "Acme Corp",
            "reference":      "YOUR-REF-001"          (your internal reference, stored in instructions)
        }

        Response 201:
        {
            "success": true,
            "tracking_number": "WRX-2604-A3F7B1",
            "order_id":        "WRX-2604-A3F7B1",
            "status":          "pending"
        }
        """
        body = request.get_json(silent=True) or {}

        # ── Required field validation ──────────────────────────────────────
        required = ['customer_name', 'email', 'phone', 'address', 'suburb', 'postcode']
        missing = [f for f in required if not str(body.get(f, '')).strip()]
        if missing:
            return jsonify({
                'success': False,
                'error': f"Missing required fields: {', '.join(missing)}",
            }), 400

        # ── Build instructions string (include external reference if given) ──
        instructions_parts = []
        if body.get('reference'):
            instructions_parts.append(f"[REF:{body['reference']}]")
        if body.get('instructions'):
            instructions_parts.append(body['instructions'])
        instructions = ' '.join(instructions_parts).strip()

        order_data = {
            'customer':            str(body['customer_name']).strip(),
            'delivery_company':    str(body.get('company', '')).strip(),
            'email':               str(body['email']).strip(),
            'phone':               str(body['phone']).strip(),
            'address':             str(body['address']).strip(),
            'address2':            str(body.get('address2', '')).strip(),
            'suburb':              str(body['suburb']).strip(),
            'state':               str(body.get('state', 'NSW')).strip() or 'NSW',
            'postcode':            str(body['postcode']).strip(),
            'country':             str(body.get('country', 'Australia')).strip(),
            'parcels':             int(body.get('parcels', 1)),
            'service_level':       str(body.get('service_level', 'standard')).strip(),
            'instructions':        instructions,
            'special_instructions': instructions,
            'zone':                str(body.get('zone', '')).strip(),
        }

        if body.get('weight') is not None:
            try:
                order_data['weight'] = float(body['weight'])
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'weight must be a number (kg)'}), 400

        try:
            result = data_manager.create_order(order_data)
        except Exception as exc:
            logger.error(f"[external-api] create_order failed: {exc}", exc_info=True)
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', 'Order creation failed')}), 500

        tracking = result['tracking_number']
        logger.info(f"[external-api] Order {tracking} created via partner API")

        return jsonify({
            'success':         True,
            'tracking_number': tracking,
            'order_id':        tracking,
            'status':          'pending',
        }), 201

    # ── GET /api/v1/orders/<tracking_number> ─────────────────────────────────
    @app.route('/api/v1/orders/<tracking_number>', methods=['GET'])
    @_require_api_key
    def external_get_order(tracking_number):
        """
        Retrieve current status and details for an order.

        Response 200:
        {
            "success": true,
            "order": {
                "tracking_number": "WRX-2604-A3F7B1",
                "status":          "in_transit",
                "customer":        "Jane Smith",
                "address":         "123 George St",
                "suburb":          "Sydney",
                "postcode":        "2000",
                "parcels":         1,
                "service_level":   "standard",
                "created_at":      "2026-04-09T10:00:00",
                "driver_id":       "DRV-706"
            }
        }
        """
        try:
            order = data_manager.store.get_order_by_tracking(tracking_number)
        except Exception as exc:
            logger.error(f"[external-api] get_order failed: {exc}", exc_info=True)
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

        if order is None:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        # Normalise to plain dict regardless of store version
        if hasattr(order, 'to_dict'):
            order = order.to_dict()
        else:
            order = dict(order)

        return jsonify({
            'success': True,
            'order': {
                'tracking_number': order.get('tracking_number') or order.get('order_id'),
                'status':          order.get('status', 'pending'),
                'customer':        order.get('customer', ''),
                'address':         order.get('address', ''),
                'suburb':          order.get('suburb', ''),
                'state':           order.get('state', ''),
                'postcode':        order.get('postcode', ''),
                'parcels':         order.get('parcels', 1),
                'weight':          order.get('weight'),
                'service_level':   order.get('service_level', 'standard'),
                'created_at':      str(order.get('created_at', '')),
                'driver_id':       order.get('driver_id', ''),
            },
        }), 200

    # ── GET /api/v1/orders/<tracking_number>/track ────────────────────────────
    @app.route('/api/v1/orders/<tracking_number>/track', methods=['GET'])
    @_require_api_key
    def external_track_order(tracking_number):
        """
        Return a simple tracking timeline for an order.

        Response 200:
        {
            "success": true,
            "tracking_number": "WRX-2604-A3F7B1",
            "current_status": "in_transit",
            "timeline": [
                {"status": "pending",    "label": "Order Received",     "completed": true},
                {"status": "allocated",  "label": "Driver Assigned",    "completed": true},
                {"status": "in_transit", "label": "Out For Delivery",   "completed": true},
                {"status": "delivered",  "label": "Delivered",          "completed": false}
            ]
        }
        """
        try:
            order = data_manager.store.get_order_by_tracking(tracking_number)
        except Exception as exc:
            logger.error(f"[external-api] track_order failed: {exc}", exc_info=True)
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

        if order is None:
            return jsonify({'success': False, 'error': 'Order not found'}), 404

        if hasattr(order, 'to_dict'):
            order = order.to_dict()
        else:
            order = dict(order)

        current = order.get('status', 'pending')

        steps = [
            ('pending',    'Order Received'),
            ('allocated',  'Driver Assigned'),
            ('in_transit', 'Out For Delivery'),
            ('delivered',  'Delivered'),
        ]
        if current == 'failed':
            steps.append(('failed', 'Delivery Failed'))

        order_reached = False
        timeline = []
        for status, label in steps:
            if status == current:
                order_reached = True
            timeline.append({
                'status':    status,
                'label':     label,
                'completed': not order_reached or status == current,
            })
            if order_reached and status != current:
                timeline[-1]['completed'] = False

        # Simpler approach — just mark everything up to and including current as completed
        reached = False
        for item in timeline:
            if not reached:
                item['completed'] = True
            if item['status'] == current:
                reached = True
                item['completed'] = True
            elif reached:
                item['completed'] = False

        return jsonify({
            'success':         True,
            'tracking_number': tracking_number,
            'current_status':  current,
            'timeline':        timeline,
        }), 200

    logger.info("✅ External partner API registered at /api/v1/")
