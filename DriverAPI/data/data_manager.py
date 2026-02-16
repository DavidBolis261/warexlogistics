import random
import json
import hashlib
import secrets
import os
from datetime import datetime, timedelta

import pandas as pd

from config.settings import wms_config
from data.local_store import LocalStore
from data.mock_data import generate_mock_orders, generate_mock_drivers, generate_mock_runs
from api.client import DotWmsClient
from api.fulfilment import upsert_fulfilment_request, cancel_sales_order
from api.receipts import upsert_asn_receipt, cancel_receipt as api_cancel_receipt
from api.inventory import upsert_item_master_data, delete_item_master_data
from api.stock import adjust_uld_stock, create_uld as api_create_uld, destroy_uld as api_destroy_uld, move_uld as api_move_uld
from utils.email_service import send_order_confirmation, send_status_update, is_email_configured
from api.logistics import create_kitting_job as api_create_kitting_job


class DataManager:
    """Unified data access layer.

    Decides between:
    - PostgreSQL (Production): when DATABASE_URL is set
    - SQLite (Development): local file-based database
    - Demo mode: use mock data generators
    """

    def __init__(self):
        # Auto-detect database type
        database_url = os.environ.get('DATABASE_URL')

        if database_url:
            # Use PostgreSQL for production
            from data.postgres_store import PostgresStore
            self.store = PostgresStore(database_url)
            print("✅ Using PostgreSQL database (Production)")
        else:
            # Use SQLite for local development
            self.store = LocalStore()
            print("✅ Using SQLite database (Development)")

        self._client = None
        # Seed default zones on first init
        self.store.seed_default_zones()

    @property
    def client(self):
        if self._client is None and wms_config.is_configured:
            self._client = DotWmsClient(wms_config)
        return self._client

    @property
    def is_live(self):
        return wms_config.is_configured and self.client is not None

    @property
    def data_mode(self):
        import streamlit as st
        mode = st.session_state.get('data_mode', 'Local Only (SQLite)')
        if 'Live' in mode and self.is_live:
            return 'live'
        elif 'Local' in mode:
            return 'local'
        return 'demo'

    # === Orders ===

    def get_orders(self):
        if self.data_mode == 'demo':
            return generate_mock_orders(50)
        return self.store.get_orders()

    def create_order(self, order_data):
        order_id = f"SMC-{random.randint(10000, 99999)}"
        tracking_number = self._generate_tracking_number()
        order_data['order_id'] = order_id
        order_data['tracking_number'] = tracking_number
        order_data['status'] = 'pending'
        order_data['created_at'] = datetime.now().isoformat()
        order_data['order_date'] = datetime.now().strftime('%Y-%m-%d')

        wms_result = None
        pushed = False

        if self.data_mode == 'live':
            wms_result = upsert_fulfilment_request(self.client, order_data)
            pushed = wms_result.get('success', False)
            self.store.log_api_call(
                operation='UpsertFulfilmentRequest',
                endpoint=f"{wms_config.base_url}/UpsertFulfilmentRequest/",
                request_summary=f"Order {order_id} for {order_data['customer']}",
                success=pushed,
                status_code=wms_result.get('status_code'),
                response_body=json.dumps(wms_result.get('response', '')),
                error_message=wms_result.get('error'),
            )

        self.store.save_order(order_data, wms_response=wms_result, pushed=pushed)

        # Send confirmation email if configured and customer has email
        email_sent = False
        if order_data.get('email') and is_email_configured(self):
            result = send_order_confirmation(self, order_data)
            email_sent = result.get('success', False)

        return {
            'success': True,
            'order_id': order_id,
            'tracking_number': tracking_number,
            'wms_pushed': pushed,
            'email_sent': email_sent,
            'mock': self.data_mode == 'demo',
        }

    def push_order_to_wms(self, order_data):
        if not self.is_live:
            return {'success': False, 'mock': True, 'error': 'WMS not configured'}

        result = upsert_fulfilment_request(self.client, order_data)
        self.store.log_api_call(
            operation='UpsertFulfilmentRequest',
            endpoint=f"{wms_config.base_url}/UpsertFulfilmentRequest/",
            request_summary=f"Push order {order_data.get('order_id', 'unknown')}",
            success=result.get('success', False),
            status_code=result.get('status_code'),
            response_body=json.dumps(result.get('response', '')),
            error_message=result.get('error'),
        )

        if result.get('success'):
            self.store.save_order(order_data, wms_response=result, pushed=True)

        return result

    def cancel_order(self, order_id):
        if self.is_live:
            result = cancel_sales_order(self.client, order_id)
            self.store.log_api_call(
                operation='CancelSalesOrder',
                endpoint=f"{wms_config.base_url}/CancelSalesOrder/",
                request_summary=f"Cancel order {order_id}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            if not result.get('success'):
                return result

        self.store.update_order_status(order_id, 'failed')
        return {'success': True}

    def allocate_order(self, order_id, driver_name):
        self.store.update_order_status(order_id, 'allocated', driver_id=driver_name)

    def update_order(self, order_id, **fields):
        """Update order fields (status, zone, driver_id, etc.)."""
        self.store.update_order_fields(order_id, **fields)

        # Send status update email if status changed
        if 'status' in fields and is_email_configured(self):
            order = self.store.get_order_by_id(order_id)
            if order and order.get('email'):
                send_status_update(self, dict(order), fields['status'])

    # === Drivers ===

    def get_drivers(self):
        if self.data_mode == 'demo':
            return generate_mock_drivers(10)
        return self.store.get_drivers()

    def add_driver(self, driver_data):
        driver_id = f"DRV-{random.randint(100, 999)}"
        driver_data['driver_id'] = driver_id
        self.store.save_driver(driver_data)
        return {'success': True, 'driver_id': driver_id}

    def update_driver(self, driver_id, driver_data):
        self.store.update_driver(driver_id, driver_data)
        return {'success': True}

    def delete_driver(self, driver_id):
        self.store.delete_driver(driver_id)
        return {'success': True}

    def update_driver_location(self, driver_id, latitude, longitude, timestamp=None):
        """Update driver's current location for real-time tracking."""
        self.store.update_driver_location(driver_id, latitude, longitude, timestamp)
        return {'success': True}

    # === Runs ===

    def get_runs(self):
        if self.data_mode == 'demo':
            return generate_mock_runs(15)
        return self.store.get_runs()

    def create_run(self, zone, driver_id, driver_name, order_ids):
        today = datetime.now().strftime('%y%m%d')
        count = self.store.count_runs_today()
        run_id = f"RUN-{today}-{count + 1:03d}"

        run_data = {
            'run_id': run_id,
            'zone': zone,
            'driver_id': driver_id,
            'driver_name': driver_name,
            'status': 'active',
            'total_stops': len(order_ids),
            'completed': 0,
        }
        self.store.save_run(run_data)
        self.store.save_run_orders(run_id, order_ids)

        # Update each order's status to allocated
        for oid in order_ids:
            self.store.update_order_status(oid, 'allocated', driver_id=driver_name)

        return {'success': True, 'run_id': run_id}

    def update_run_progress(self, run_id, completed):
        self.store.update_run_progress(run_id, completed)
        return {'success': True}

    def complete_run(self, run_id):
        self.store.update_run_status(run_id, 'completed')
        # Mark all orders in this run as delivered
        run_orders = self.store.get_run_orders(run_id)
        if not run_orders.empty:
            for _, ro in run_orders.iterrows():
                self.store.update_order_status(ro['order_id'], 'delivered')
            self.store.update_run_progress(run_id, len(run_orders))
        return {'success': True}

    def cancel_run(self, run_id):
        self.store.update_run_status(run_id, 'cancelled')
        # Revert orders back to pending
        run_orders = self.store.get_run_orders(run_id)
        if not run_orders.empty:
            for _, ro in run_orders.iterrows():
                self.store.update_order_status(ro['order_id'], 'pending')
        return {'success': True}

    def get_run_orders(self, run_id):
        return self.store.get_run_orders(run_id)

    # === Settings ===

    def get_setting(self, key, default=None):
        return self.store.get_setting(key, default)

    def get_all_settings(self):
        return self.store.get_all_settings()

    def save_settings(self, settings_dict):
        self.store.set_settings_bulk(settings_dict)

    # === Zones ===

    def get_zones(self):
        return self.store.get_zones()

    def save_zone(self, zone_data):
        self.store.save_zone(zone_data)

    def delete_zone(self, zone_name):
        self.store.delete_zone(zone_name)

    # === Receipts ===

    def get_receipts(self):
        if self.data_mode == 'demo':
            return pd.DataFrame()
        return self.store.get_receipts()

    def create_receipt(self, receipt_data):
        wms_result = None
        pushed = False

        if self.data_mode == 'live':
            wms_result = upsert_asn_receipt(self.client, receipt_data)
            pushed = wms_result.get('success', False)
            self.store.log_api_call(
                operation='UpsertASNReceipt',
                endpoint=f"{wms_config.base_url}/UpsertASNReceipt/",
                request_summary=f"Receipt {receipt_data['shipment_number']}",
                success=pushed,
                status_code=wms_result.get('status_code'),
                response_body=json.dumps(wms_result.get('response', '')),
                error_message=wms_result.get('error'),
            )

        self.store.save_receipt(receipt_data, wms_response=wms_result, pushed=pushed)
        return {
            'success': True,
            'wms_pushed': pushed,
        }

    def cancel_receipt(self, shipment_number, reason=''):
        if self.is_live:
            result = api_cancel_receipt(self.client, shipment_number, reason)
            self.store.log_api_call(
                operation='CancelReceiptJob',
                endpoint=f"{wms_config.base_url}/CancelReceiptJob/",
                request_summary=f"Cancel receipt {shipment_number}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    # === Items ===

    def get_items(self):
        if self.data_mode == 'demo':
            return pd.DataFrame()
        return self.store.get_items()

    def upsert_item(self, item_data):
        wms_result = None
        pushed = False

        if self.data_mode == 'live':
            wms_result = upsert_item_master_data(self.client, item_data)
            pushed = wms_result.get('success', False)
            self.store.log_api_call(
                operation='UpsertItemMasterData',
                endpoint=f"{wms_config.base_url}/UpsertItemMasterData/",
                request_summary=f"Item {item_data['item_code']}",
                success=pushed,
                status_code=wms_result.get('status_code'),
                response_body=json.dumps(wms_result.get('response', '')),
                error_message=wms_result.get('error'),
            )

        self.store.save_item(item_data, wms_response=wms_result, pushed=pushed)
        return {'success': True, 'wms_pushed': pushed}

    def delete_item(self, item_code):
        if self.is_live:
            result = delete_item_master_data(self.client, item_code)
            self.store.log_api_call(
                operation='DeleteItemMasterData',
                endpoint=f"{wms_config.base_url}/DeleteItemMasterData/",
                request_summary=f"Delete item {item_code}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            if not result.get('success'):
                return result

        self.store.delete_item(item_code)
        return {'success': True}

    # === Stock / ULD ===

    def adjust_stock(self, adjustment_data):
        if self.is_live:
            result = adjust_uld_stock(self.client, adjustment_data)
            self.store.log_api_call(
                operation='AdjustULDStock',
                endpoint=f"{wms_config.base_url}/AdjustULDStock/",
                request_summary=f"Adjust {adjustment_data['item_code']} on {adjustment_data['uld_barcode']}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    def create_uld(self, uld_data):
        if self.is_live:
            result = api_create_uld(self.client, uld_data)
            self.store.log_api_call(
                operation='CreateULD',
                endpoint=f"{wms_config.base_url}/CreateULD/",
                request_summary=f"Create ULD {uld_data.get('barcode', 'auto')}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    def destroy_uld(self, uld_barcode):
        if self.is_live:
            result = api_destroy_uld(self.client, uld_barcode)
            self.store.log_api_call(
                operation='DestroyULD',
                endpoint=f"{wms_config.base_url}/DestroyULD/",
                request_summary=f"Destroy ULD {uld_barcode}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    def move_uld(self, uld_barcode, new_location):
        if self.is_live:
            result = api_move_uld(self.client, uld_barcode, new_location)
            self.store.log_api_call(
                operation='MoveULD',
                endpoint=f"{wms_config.base_url}/MoveULD/",
                request_summary=f"Move ULD {uld_barcode} to {new_location}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    def create_kitting_job(self, job_data):
        if self.is_live:
            result = api_create_kitting_job(self.client, job_data)
            self.store.log_api_call(
                operation='UploadKitJob',
                endpoint=f"{wms_config.base_url}/UploadKitJob/",
                request_summary=f"Kitting job {job_data['pack_slip_number']}",
                success=result.get('success', False),
                status_code=result.get('status_code'),
                response_body=json.dumps(result.get('response', '')),
                error_message=result.get('error'),
            )
            return result
        return {'success': True, 'mock': True}

    # === Connection ===

    def test_wms_connection(self):
        if not self.is_live:
            return {'success': False, 'error': 'WMS not configured'}
        result = self.client.test_connection()
        self.store.log_api_call(
            operation='TestConnection',
            endpoint=wms_config.base_url,
            request_summary='Connection test',
            success=result.get('success', False),
            error_message=result.get('error'),
        )
        return result

    # === API Log ===

    def get_api_log(self):
        return self.store.get_api_log()

    def clear_api_log(self):
        self.store.clear_api_log()

    # === Tracking ===

    def _generate_tracking_number(self):
        """Generate a unique tracking number like WRX-2602-A3F7B1."""
        prefix = datetime.now().strftime('%y%m')
        for _ in range(10):
            hex_part = secrets.token_hex(3).upper()
            tracking = f"WRX-{prefix}-{hex_part}"
            if not self.store.tracking_number_exists(tracking):
                return tracking
        raise RuntimeError("Failed to generate unique tracking number")

    def get_order_by_tracking(self, tracking_number):
        return self.store.get_order_by_tracking(tracking_number)

    # === Authentication ===

    def _hash_password(self, password, salt=None):
        """Hash a password with SHA-256 + salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return pw_hash, salt

    def authenticate(self, username, password):
        """Verify username/password. Returns session token if valid, None otherwise."""
        user = self.store.get_admin_user(username)
        if not user:
            return None
        pw_hash, _ = self._hash_password(password, user['salt'])
        if pw_hash != user['password_hash']:
            return None
        # Create a session token valid for 7 days
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(days=7)).isoformat()
        self.store.create_session_token(token, user['username'], expires)
        return token

    def validate_session_token(self, token):
        """Check if a session token is valid and not expired."""
        if not token:
            return False
        session = self.store.get_session_token(token)
        return session is not None

    def logout_token(self, token):
        """Invalidate a session token."""
        if token:
            self.store.delete_session_token(token)

    def create_admin(self, username, password):
        """Create an admin user. Returns dict with success and optional token."""
        if self.store.get_admin_user(username):
            return {'success': False, 'error': 'Username already exists'}
        pw_hash, salt = self._hash_password(password)
        self.store.create_admin_user(username, pw_hash, salt)
        # Auto-login: create session token
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(days=7)).isoformat()
        self.store.create_session_token(token, username, expires)
        return {'success': True, 'token': token}

    def admin_exists(self):
        """Check if any admin user exists."""
        return self.store.admin_user_count() > 0
