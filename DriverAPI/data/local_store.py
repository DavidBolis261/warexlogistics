import sqlite3
import json
import os
import secrets
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
        self._migrate()

    def _create_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                tracking_number TEXT UNIQUE,
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
                pickup_address TEXT,
                pickup_suburb TEXT,
                pickup_state TEXT,
                pickup_postcode TEXT,
                pickup_contact TEXT,
                pickup_phone TEXT,
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

            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS session_tokens (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS driver_tokens (
                token TEXT PRIMARY KEY,
                driver_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT NOT NULL,
                driver_name TEXT,
                body TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'inbound',
                is_read INTEGER DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_orders_driver_id ON orders(driver_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_orders_zone ON orders(zone);
            CREATE INDEX IF NOT EXISTS idx_run_orders_run_id ON run_orders(run_id);
            CREATE INDEX IF NOT EXISTS idx_run_orders_order_id ON run_orders(order_id);
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_runs_driver_id ON runs(driver_id);
            CREATE INDEX IF NOT EXISTS idx_session_tokens_expires_at ON session_tokens(expires_at);
            CREATE INDEX IF NOT EXISTS idx_messages_driver_id ON messages(driver_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
        ''')
        self.conn.commit()

    def _migrate(self):
        """Add columns that may not exist in older databases."""
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(orders)").fetchall()}
        new_cols = {
            'pickup_address': 'TEXT',
            'pickup_suburb': 'TEXT',
            'pickup_state': 'TEXT',
            'pickup_postcode': 'TEXT',
            'pickup_contact': 'TEXT',
            'pickup_phone': 'TEXT',
            'tracking_number': 'TEXT',
            'zone': 'TEXT',
            # Proof-of-delivery fields written by the driver mobile app
            'proof_photo': 'TEXT',
            'proof_signature': 'TEXT',
            'delivery_notes': 'TEXT',
            # Delivery completion timestamp (set when status → delivered)
            'delivered_at': 'TEXT',
        }
        for col, col_type in new_cols.items():
            if col not in existing:
                self.conn.execute(f"ALTER TABLE orders ADD COLUMN {col} {col_type}")

        # Add unique index on tracking_number if column was just added
        if 'tracking_number' not in existing:
            try:
                self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tracking_number ON orders(tracking_number)")
            except sqlite3.OperationalError:
                pass

        self.conn.commit()

        # Migrate drivers table — add location columns if missing
        driver_existing = {row[1] for row in self.conn.execute("PRAGMA table_info(drivers)").fetchall()}
        driver_new_cols = {
            'latitude': 'REAL',
            'longitude': 'REAL',
            'location_updated_at': 'TEXT',
        }
        for col, col_type in driver_new_cols.items():
            if col not in driver_existing:
                try:
                    self.conn.execute(f"ALTER TABLE drivers ADD COLUMN {col} {col_type}")
                except Exception:
                    pass
        self.conn.commit()

        # Backfill tracking numbers for existing orders that don't have one
        null_orders = self.conn.execute(
            "SELECT order_id FROM orders WHERE tracking_number IS NULL"
        ).fetchall()
        if null_orders:
            prefix = datetime.now().strftime('%y%m')
            for row in null_orders:
                tracking = f"WRX-{prefix}-{secrets.token_hex(3).upper()}"
                self.conn.execute(
                    "UPDATE orders SET tracking_number = ? WHERE order_id = ?",
                    (tracking, row['order_id']),
                )
            self.conn.commit()

    # === Orders ===

    def save_order(self, order_data, wms_response=None, pushed=False):
        self.conn.execute('''
            INSERT OR REPLACE INTO orders
            (order_id, tracking_number, customer, delivery_company, address, address2, suburb, state, postcode,
             country, email, phone, status, service_level, parcels, item_code,
             driver_id, carrier_service, special_instructions,
             pickup_address, pickup_suburb, pickup_state, pickup_postcode, pickup_contact, pickup_phone,
             eta, pushed_to_wms, wms_response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data.get('order_id'),
            order_data.get('tracking_number'),
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
            order_data.get('pickup_address'),
            order_data.get('pickup_suburb'),
            order_data.get('pickup_state'),
            order_data.get('pickup_postcode'),
            order_data.get('pickup_contact'),
            order_data.get('pickup_phone'),
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

    def update_order_fields(self, order_id, **fields):
        """Update arbitrary fields on an order."""
        if not fields:
            return
        set_clauses = ', '.join(f"{k}=?" for k in fields)
        values = list(fields.values())
        values.append(datetime.now().isoformat())
        values.append(order_id)
        self.conn.execute(
            f"UPDATE orders SET {set_clauses}, updated_at=? WHERE order_id=?",
            values,
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

    def update_driver_location(self, driver_id, latitude, longitude, timestamp=None):
        """Update driver's current location for real-time tracking."""
        from datetime import datetime as dt

        if timestamp is None:
            timestamp = dt.now().isoformat()

        self.conn.execute('''
            UPDATE drivers
            SET latitude = ?,
                longitude = ?,
                location_updated_at = ?
            WHERE driver_id = ?
        ''', (latitude, longitude, timestamp, driver_id))
        self.conn.commit()

    def get_drivers(self):
        """Get all drivers with real-time calculated statistics from orders."""
        drivers_df = pd.read_sql_query("SELECT * FROM drivers ORDER BY name", self.conn)

        if drivers_df.empty:
            return drivers_df

        today = datetime.now().strftime('%Y-%m-%d')

        # Single aggregation query replaces N+1 per-driver queries
        stats_df = pd.read_sql_query(
            """
            SELECT
                driver_id,
                SUM(CASE WHEN status IN ('allocated', 'in_transit') THEN 1 ELSE 0 END) AS active_orders,
                SUM(CASE WHEN status = 'delivered' AND substr(created_at, 1, 10) = ? THEN 1 ELSE 0 END) AS deliveries_today,
                SUM(CASE WHEN status IN ('delivered', 'failed') THEN 1 ELSE 0 END) AS total_completed,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS total_delivered
            FROM orders
            WHERE driver_id IS NOT NULL
            GROUP BY driver_id
            """,
            self.conn,
            params=(today,)
        )

        # Drop stale stat columns from the drivers table so the merge never
        # produces _x / _y suffixes and the columns are always present.
        stat_cols = ['active_orders', 'deliveries_today', 'total_completed', 'total_delivered']
        drivers_df = drivers_df.drop(
            columns=[c for c in stat_cols if c in drivers_df.columns],
            errors='ignore',
        )

        if stats_df.empty:
            drivers_df['active_orders'] = 0
            drivers_df['deliveries_today'] = 0
            return drivers_df

        drivers_df = drivers_df.merge(stats_df, on='driver_id', how='left')

        # Fill NaN for drivers that have no matching orders
        drivers_df['active_orders'] = drivers_df['active_orders'].fillna(0).astype(int)
        drivers_df['deliveries_today'] = drivers_df['deliveries_today'].fillna(0).astype(int)
        drivers_df['total_completed'] = drivers_df['total_completed'].fillna(0)
        drivers_df['total_delivered'] = drivers_df['total_delivered'].fillna(0)

        # Vectorized success rate calculation
        has_completed = drivers_df['total_completed'] > 0
        drivers_df.loc[has_completed, 'success_rate'] = (
            drivers_df.loc[has_completed, 'total_delivered'] /
            drivers_df.loc[has_completed, 'total_completed']
        )

        drivers_df = drivers_df.drop(columns=['total_completed', 'total_delivered'])
        return drivers_df

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
            # Vectorized progress calculation
            df['progress'] = 0.0
            has_stops = df['total_stops'] > 0
            df.loc[has_stops, 'progress'] = (
                df.loc[has_stops, 'completed'] / df.loc[has_stops, 'total_stops'] * 100
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

    # === Admin Users ===

    def create_admin_user(self, username, password_hash, salt):
        self.conn.execute(
            "INSERT INTO admin_users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt),
        )
        self.conn.commit()

    def get_admin_user(self, username):
        return self.conn.execute(
            "SELECT * FROM admin_users WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()

    def admin_user_count(self):
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM admin_users").fetchone()
        return row['cnt'] if row else 0

    # === Session Tokens ===

    def create_session_token(self, token, username, expires_at):
        self.conn.execute(
            "INSERT OR REPLACE INTO session_tokens (token, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, username, datetime.now().isoformat(), expires_at),
        )
        self.conn.commit()

    def get_session_token(self, token):
        return self.conn.execute(
            "SELECT * FROM session_tokens WHERE token = ? AND expires_at > ?",
            (token, datetime.now().isoformat()),
        ).fetchone()

    def delete_session_token(self, token):
        self.conn.execute("DELETE FROM session_tokens WHERE token = ?", (token,))
        self.conn.commit()

    def cleanup_expired_tokens(self):
        self.conn.execute("DELETE FROM session_tokens WHERE expires_at < ?", (datetime.now().isoformat(),))
        self.conn.commit()

    # Driver auth tokens
    def save_driver_token(self, token, driver_id, phone, expires_at):
        self.conn.execute(
            "INSERT OR IGNORE INTO driver_tokens (token, driver_id, phone, expires_at) VALUES (?, ?, ?, ?)",
            (token, driver_id, phone, expires_at),
        )
        self.conn.commit()

    def get_driver_token(self, token):
        row = self.conn.execute(
            "SELECT driver_id, phone, expires_at FROM driver_tokens WHERE token = ? AND expires_at > ?",
            (token, datetime.now().isoformat()),
        ).fetchone()
        if row is None:
            return None
        return {'driver_id': row['driver_id'], 'phone': row['phone'], 'expires': row['expires_at']}

    def delete_driver_token(self, token):
        self.conn.execute("DELETE FROM driver_tokens WHERE token = ?", (token,))
        self.conn.commit()

    def purge_expired_driver_tokens(self):
        self.conn.execute("DELETE FROM driver_tokens WHERE expires_at <= ?", (datetime.now().isoformat(),))
        self.conn.commit()

    # === Tracking ===

    def tracking_number_exists(self, tracking_number):
        row = self.conn.execute(
            "SELECT 1 FROM orders WHERE tracking_number = ?", (tracking_number,)
        ).fetchone()
        return row is not None

    def get_order_by_tracking(self, tracking_number):
        row = self.conn.execute(
            "SELECT * FROM orders WHERE tracking_number = ?", (tracking_number,)
        ).fetchone()
        return dict(row) if row else None

    def get_order_by_id(self, order_id):
        row = self.conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return dict(row) if row else None

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

    # === Messages ===

    def save_message(self, driver_id, driver_name, body, direction='inbound'):
        """Save a driver↔admin message. direction: 'inbound' = driver→admin, 'outbound' = admin→driver."""
        from datetime import timezone
        sent_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO messages (driver_id, driver_name, body, direction, is_read, sent_at) VALUES (?, ?, ?, ?, 0, ?)",
            (driver_id, driver_name, body, direction, sent_at),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT last_insert_rowid() as id").fetchone()
        return row['id'] if row else None

    def get_messages_for_driver(self, driver_id, limit=100):
        """Get all messages for a specific driver (conversation thread)."""
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE driver_id = ? ORDER BY sent_at ASC LIMIT ?",
            (driver_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_unread_count(self, driver_id=None):
        """Count unread outbound messages (admin→driver) for a driver."""
        if driver_id:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE driver_id=? AND direction='outbound' AND is_read=0",
                (driver_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE direction='outbound' AND is_read=0"
            ).fetchone()
        return row['cnt'] if row else 0

    def mark_messages_read(self, driver_id):
        """Mark all outbound messages to a driver as read (driver has seen them)."""
        self.conn.execute(
            "UPDATE messages SET is_read=1 WHERE driver_id=? AND direction='outbound'",
            (driver_id,),
        )
        self.conn.commit()
