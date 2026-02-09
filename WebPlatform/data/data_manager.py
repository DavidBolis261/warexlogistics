import random
import json
from datetime import datetime

import pandas as pd

from config.settings import wms_config
from data.local_store import LocalStore
from data.mock_data import generate_mock_orders, generate_mock_drivers, generate_mock_runs
from api.client import DotWmsClient
from api.fulfilment import upsert_fulfilment_request, cancel_sales_order
from api.receipts import upsert_asn_receipt, cancel_receipt as api_cancel_receipt
from api.inventory import upsert_item_master_data, delete_item_master_data
from api.stock import adjust_uld_stock, create_uld as api_create_uld, destroy_uld as api_destroy_uld, move_uld as api_move_uld
from api.logistics import create_kitting_job as api_create_kitting_job


class DataManager:
    """Unified data access layer.

    Decides between:
    - Live mode: push to .wms API + save to local store
    - Local mode: save to local SQLite only
    - Demo mode: use mock data generators
    """

    def __init__(self):
        self.store = LocalStore()
        self._client = None

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
        mode = st.session_state.get('data_mode', '')
        if 'Live' in mode and self.is_live:
            return 'live'
        elif 'Local' in mode:
            return 'local'
        return 'demo'

    # === Orders ===

    def get_orders(self):
        if self.data_mode == 'demo':
            return generate_mock_orders(50)
        orders = self.store.get_orders()
        if orders.empty:
            return generate_mock_orders(50)
        return orders

    def create_order(self, order_data):
        order_id = f"SMC-{random.randint(10000, 99999)}"
        order_data['order_id'] = order_id
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

        return {
            'success': True,
            'order_id': order_id,
            'wms_pushed': pushed,
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

    # === Drivers ===

    def get_drivers(self):
        if self.data_mode == 'demo':
            return generate_mock_drivers(10)
        drivers = self.store.get_drivers()
        if drivers.empty:
            return generate_mock_drivers(10)
        return drivers

    def add_driver(self, driver_data):
        driver_id = f"DRV-{random.randint(100, 999)}"
        driver_data['driver_id'] = driver_id
        self.store.save_driver(driver_data)
        return {'success': True, 'driver_id': driver_id}

    # === Runs ===

    def get_runs(self):
        return generate_mock_runs(15)

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
