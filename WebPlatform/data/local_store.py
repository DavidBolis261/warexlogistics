import sqlite3
import json
import os
from datetime import datetime

import pandas as pd


class LocalStore:
    """SQLite-backed local persistence for orders, receipts, items, drivers, runs, settings, zones, and API logs."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.environ.get(
                'DATABASE_PATH',
                os.path.join(os.path.dirname(__file__), '..', 'courier.db'),
            )
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer TEXT,
                delivery_company TEXT,
                address TEXT,
                address2 TEXT,
                suburb TEXT,
                state TEXT DEFAULT 'NSW',
                postcode TEXT,
                country TEXT DEFAULT 'Australia',
                email TEXT,
                phone TEXT,
                status TEXT DEFAULT 'pending',
                service_level TEXT DEFAULT 'standard',
                parcels INTEGER DEFAULT 1,
                item_code TEXT DEFAULT 'PARCEL',
                driver_id TEXT,
                carrier_service TEXT,
                special_instructions TEXT,
                eta TEXT,
                pushed_to_wms INTEGER DEFAULT 0,
                wms_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS receipts (
                shipment_number TEXT PRIMARY KEY,
                supplier_name TEXT,
                receipt_reference TEXT,
                container_type TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                lines_json TEXT,
                pushed_to_wms INTEGER DEFAULT 0,
                wms_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS items (
                item_code TEXT PRIMARY KEY,
                item_name TEXT,
                item_group TEXT,
                barcode TEXT,
                weight REAL,
                length REAL,
                width REAL,
                height REAL,
                unit_of_measure TEXT,
                inner_qty INTEGER,
                outer_qty INTEGER,
                pallet_qty INTEGER,
                pushed_to_wms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS drivers (
                driver_id TEXT PRIMARY KEY,
                name TEXT,
                vehicle_type TEXT,
                plate TEXT,
                status TEXT DEFAULT 'available',
                current_zone TEXT,
                phone TEXT,
                deliveries_today INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.95,
                rating REAL DEFAULT 4.5,
                active_orders INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                zone TEXT,
                driver_id TEXT,
                driver_name TEXT,
                status TEXT DEFAULT 'active',
                total_stops INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS run_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                stop_sequence INTEGER,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (run_id) REFERENCES runs(run_id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS zones (
                zone_name TEXT PRIMARY KEY,
                suburbs TEXT,
                postcodes TEXT,
                surcharge REAL DEFAULT 0.0,
                max_stops INTEGER DEFAULT 15,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                operation TEXT,
                endpoint TEXT,
                request_summary TEXT,
                success INTEGER,
                status_code INTEGER,
                response_body TEXT,
                error_message TEXT
            );
        ''')
        self.conn.commit()

    # === Orders ===

    def save_order(self, order_data, wms_response=None, pushed=False):
        self.conn.execute('''
            INSERT OR REPLACE INTO orders
            (order_id, customer, delivery_company, address, address2, suburb, state, postcode,
             country, email, phone, status, service_level, parcels, item_code,
             driver_id, carrier_service, special_instructions, eta,
             pushed_to_wms, wms_response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data.get('order_id'),
            order_data.get('customer'),
            order_data.get('delivery_company'),
            order_data.get('address'),
            order_data.get('address2'),
            order_data.get('suburb'),
            order_data.get('state', 'NSW'),
            order_data.get('postcode'),
            order_data.get('country', 'Australia'),
            order_data.get('email'),
            order_data.get('phone'),
            order_data.get('status', 'pending'),
            order_data.get('service_level', 'standard'),
            order_data.get('parcels', 1),
            order_data.get('item_code', 'PARCEL'),
            order_data.get('driver_id'),
            order_data.get('carrier_service'),
            order_data.get('special_instructions'),
            order_data.get('eta'),
            1 if pushed else 0,
            json.dumps(wms_response) if wms_response else None,
            order_data.get('created_at', datetime.now().isoformat()),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def get_orders(self, filters=None):
        query = "SELECT * FROM orders ORDER BY created_at DESC"
        df = pd.read_sql_query(query, self.conn)
        if df.empty:
            return df
        df['created_at'] = pd.to_datetime(df['created_at'])
        return df

    def update_order_status(self, order_id, status, driver_id=None):
        if driver_id:
            self.conn.execute(
                "UPDATE orders SET status=?, driver_id=?, updated_at=? WHERE order_id=?",
                (status, driver_id, datetime.now().isoformat(), order_id)
            )
        else:
            self.conn.execute(
                "UPDATE orders SET status=?, updated_at=? WHERE order_id=?",
                (status, datetime.now().isoformat(), order_id)
            )
        self.conn.commit()

    # === Receipts ===

    def save_receipt(self, receipt_data, wms_response=None, pushed=False):
        self.conn.execute('''
            INSERT OR REPLACE INTO receipts
            (shipment_number, supplier_name, receipt_reference, container_type,
             due_date, status, lines_json, pushed_to_wms, wms_response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            receipt_data['shipment_number'],
            receipt_data.get('supplier_name'),
            receipt_data.get('receipt_reference'),
            receipt_data.get('container_type'),
            receipt_data.get('due_date'),
            receipt_data.get('status', 'pending'),
            json.dumps(receipt_data.get('lines', [])),
            1 if pushed else 0,
            json.dumps(wms_response) if wms_response else None,
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def get_receipts(self):
        return pd.read_sql_query("SELECT * FROM receipts ORDER BY created_at DESC", self.conn)

    # === Items ===

    def save_item(self, item_data, wms_response=None, pushed=False):
        self.conn.execute('''
            INSERT OR REPLACE INTO items
            (item_code, item_name, item_group, barcode, weight, length, width, height,
             unit_of_measure, inner_qty, outer_qty, pallet_qty, pushed_to_wms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_data['item_code'],
            item_data.get('item_name'),
            item_data.get('item_group'),
            item_data.get('barcode'),
            item_data.get('weight'),
            item_data.get('length'),
            item_data.get('width'),
            item_data.get('height'),
            item_data.get('unit_of_measure'),
            item_data.get('inner_qty'),
            item_data.get('outer_qty'),
            item_data.get('pallet_qty'),
            1 if pushed else 0,
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def delete_item(self, item_code):
        self.conn.execute("DELETE FROM items WHERE item_code=?", (item_code,))
        self.conn.commit()

    def get_items(self):
        return pd.read_sql_query("SELECT * FROM items ORDER BY created_at DESC", self.conn)

    # === Drivers ===

    def save_driver(self, driver_data):
        self.conn.execute('''
            INSERT OR REPLACE INTO drivers
            (driver_id, name, vehicle_type, plate, status, current_zone, phone,
             deliveries_today, success_rate, rating, active_orders, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            driver_data.get('driver_id'),
            driver_data.get('name'),
            driver_data.get('vehicle_type'),
            driver_data.get('plate'),
            driver_data.get('status', 'available'),
            driver_data.get('current_zone'),
            driver_data.get('phone'),
            driver_data.get('deliveries_today', 0),
            driver_data.get('success_rate', 0.95),
            driver_data.get('rating', 4.5),
            driver_data.get('active_orders', 0),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def update_driver(self, driver_id, driver_data):
        self.conn.execute('''
            UPDATE drivers SET
                name=?, vehicle_type=?, plate=?, status=?, current_zone=?, phone=?
            WHERE driver_id=?
        ''', (
            driver_data.get('name'),
            driver_data.get('vehicle_type'),
            driver_data.get('plate'),
            driver_data.get('status', 'available'),
            driver_data.get('current_zone'),
            driver_data.get('phone'),
            driver_id,
        ))
        self.conn.commit()

    def delete_driver(self, driver_id):
        self.conn.execute("DELETE FROM drivers WHERE driver_id=?", (driver_id,))
        self.conn.commit()

    def get_drivers(self):
        return pd.read_sql_query("SELECT * FROM drivers ORDER BY name", self.conn)

    # === Runs ===

    def save_run(self, run_data):
        self.conn.execute('''
            INSERT OR REPLACE INTO runs
            (run_id, zone, driver_id, driver_name, status, total_stops, completed,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_data.get('run_id'),
            run_data.get('zone'),
            run_data.get('driver_id'),
            run_data.get('driver_name'),
            run_data.get('status', 'active'),
            run_data.get('total_stops', 0),
            run_data.get('completed', 0),
            run_data.get('created_at', datetime.now().isoformat()),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def save_run_orders(self, run_id, order_ids):
        for seq, oid in enumerate(order_ids, 1):
            self.conn.execute('''
                INSERT INTO run_orders (run_id, order_id, stop_sequence, status)
                VALUES (?, ?, ?, 'pending')
            ''', (run_id, oid, seq))
        self.conn.commit()

    def get_runs(self, status=None):
        if status:
            query = "SELECT * FROM runs WHERE status=? ORDER BY created_at DESC"
            df = pd.read_sql_query(query, self.conn, params=(status,))
        else:
            df = pd.read_sql_query("SELECT * FROM runs ORDER BY created_at DESC", self.conn)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
            # Calculate progress
            df['progress'] = df.apply(
                lambda r: (r['completed'] / r['total_stops'] * 100) if r['total_stops'] > 0 else 0,
                axis=1,
            )
        return df

    def get_run_orders(self, run_id):
        query = '''
            SELECT ro.*, o.customer, o.address, o.suburb, o.postcode, o.service_level, o.parcels
            FROM run_orders ro
            JOIN orders o ON ro.order_id = o.order_id
            WHERE ro.run_id = ?
            ORDER BY ro.stop_sequence
        '''
        return pd.read_sql_query(query, self.conn, params=(run_id,))

    def update_run_status(self, run_id, status):
        self.conn.execute(
            "UPDATE runs SET status=?, updated_at=? WHERE run_id=?",
            (status, datetime.now().isoformat(), run_id),
        )
        self.conn.commit()

    def update_run_progress(self, run_id, completed):
        self.conn.execute(
            "UPDATE runs SET completed=?, updated_at=? WHERE run_id=?",
            (completed, datetime.now().isoformat(), run_id),
        )
        self.conn.commit()

    def delete_run(self, run_id):
        self.conn.execute("DELETE FROM run_orders WHERE run_id=?", (run_id,))
        self.conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        self.conn.commit()

    def count_runs_today(self):
        today = datetime.now().strftime('%Y-%m-%d')
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM runs WHERE DATE(created_at) = ?",
            (today,),
        ).fetchone()
        return row['cnt'] if row else 0

    # === Settings ===

    def get_setting(self, key, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row['value'] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, str(value), datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_all_settings(self):
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {row['key']: row['value'] for row in rows}

    def set_settings_bulk(self, settings_dict):
        now = datetime.now().isoformat()
        for key, value in settings_dict.items():
            self.conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), now),
            )
        self.conn.commit()

    # === Zones ===

    def get_zones(self):
        return pd.read_sql_query("SELECT * FROM zones ORDER BY zone_name", self.conn)

    def save_zone(self, zone_data):
        self.conn.execute('''
            INSERT OR REPLACE INTO zones
            (zone_name, suburbs, postcodes, surcharge, max_stops, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            zone_data['zone_name'],
            json.dumps(zone_data.get('suburbs', [])),
            zone_data.get('postcodes', ''),
            zone_data.get('surcharge', 0.0),
            zone_data.get('max_stops', 15),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def delete_zone(self, zone_name):
        self.conn.execute("DELETE FROM zones WHERE zone_name=?", (zone_name,))
        self.conn.commit()

    def seed_default_zones(self):
        """Seed zones from constants if the table is empty."""
        from config.constants import ZONE_MAPPING, ZONE_POSTCODES
        count = self.conn.execute("SELECT COUNT(*) as cnt FROM zones").fetchone()['cnt']
        if count == 0:
            for zone_name, suburbs in ZONE_MAPPING.items():
                self.save_zone({
                    'zone_name': zone_name,
                    'suburbs': suburbs,
                    'postcodes': ZONE_POSTCODES.get(zone_name, ''),
                    'surcharge': 5.0 if zone_name == "Eastern Suburbs" else 0.0,
                    'max_stops': 15,
                })

    # === API Log ===

    def log_api_call(self, operation, endpoint, request_summary, success, status_code=None,
                     response_body=None, error_message=None):
        self.conn.execute('''
            INSERT INTO api_log
            (timestamp, operation, endpoint, request_summary, success, status_code,
             response_body, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            operation,
            endpoint,
            request_summary[:500] if request_summary else None,
            1 if success else 0,
            status_code,
            response_body[:2000] if response_body else None,
            error_message,
        ))
        self.conn.commit()

    def get_api_log(self):
        return pd.read_sql_query(
            "SELECT timestamp, operation, endpoint, success, status_code, error_message "
            "FROM api_log ORDER BY timestamp DESC LIMIT 100",
            self.conn
        )

    def clear_api_log(self):
        self.conn.execute("DELETE FROM api_log")
        self.conn.commit()
