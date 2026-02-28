"""
PostgreSQL data store for production use.
Automatically used when DATABASE_URL environment variable is present.
"""

import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)


class PostgresStore:
    """PostgreSQL-based data store for production."""

    def __init__(self, database_url=None):
        """Initialize PostgreSQL connection."""
        self.database_url = database_url or os.environ.get('DATABASE_URL')

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        # Create SQLAlchemy engine with connection timeouts for Railway
        self.engine = create_engine(
            self.database_url,
            poolclass=NullPool,  # Railway recommendation — no pool, fresh connection each time
            echo=False,
            connect_args={
                'connect_timeout': 10,         # 10s to establish connection
                'options': '-c statement_timeout=30000',  # 30s max query time
            },
        )

        # Create tables on first run
        self._create_tables()

    def _create_tables(self):
        """Create all necessary tables if they don't exist."""
        with self.engine.connect() as conn:
            # Orders table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    customer TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    suburb TEXT,
                    postcode TEXT,
                    state TEXT DEFAULT 'NSW',
                    parcels INTEGER DEFAULT 1,
                    service_level TEXT DEFAULT 'standard',
                    status TEXT DEFAULT 'pending',
                    zone TEXT,
                    driver_id TEXT,
                    instructions TEXT,
                    tracking_number TEXT,
                    order_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Drivers table
            conn.execute(text("""
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
                )
            """))

            # Runs table
            conn.execute(text("""
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
                )
            """))

            # Run orders table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS run_orders (
                    id SERIAL PRIMARY KEY,
                    run_id TEXT,
                    order_id TEXT,
                    stop_sequence INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Settings table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Zones table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS zones (
                    zone_name TEXT PRIMARY KEY,
                    suburbs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Admin users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    salt TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Session tokens table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS session_tokens (
                    token TEXT PRIMARY KEY,
                    username TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Driver auth tokens (persisted so they survive server restarts)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS driver_tokens (
                    token TEXT PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # API log table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    operation TEXT,
                    endpoint TEXT,
                    request_summary TEXT,
                    success BOOLEAN,
                    status_code INTEGER,
                    response_body TEXT,
                    error_message TEXT
                )
            """))

            # Receipts table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS receipts (
                    shipment_number TEXT PRIMARY KEY,
                    supplier TEXT,
                    expected_date TEXT,
                    status TEXT DEFAULT 'pending',
                    items_json TEXT,
                    pushed BOOLEAN DEFAULT FALSE,
                    wms_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Items table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS items (
                    item_code TEXT PRIMARY KEY,
                    description TEXT,
                    barcode TEXT,
                    category TEXT,
                    unit_of_measure TEXT,
                    pushed BOOLEAN DEFAULT FALSE,
                    wms_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Messages table (driver ↔ admin messaging)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    driver_id TEXT NOT NULL,
                    driver_name TEXT,
                    body TEXT NOT NULL,
                    direction TEXT NOT NULL DEFAULT 'inbound',
                    is_read BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            conn.commit()

        logger.info("✅ PostgreSQL tables created/verified")
        # Run column migrations in isolated transactions (safe to re-run)
        self._migrate_columns()

    def _migrate_columns(self):
        """Add new columns to existing tables.

        Uses IF NOT EXISTS (Postgres 9.6+) to avoid DuplicateColumn errors
        entirely.  Each migration still runs in its own autocommit connection
        as an extra safety net — if one fails the rest still execute.
        """
        migrations = [
            # (table, column_name, column_definition)
            ('orders', 'proof_photo',          'TEXT'),
            ('orders', 'proof_signature',      'TEXT'),
            ('orders', 'delivery_notes',       'TEXT'),
            ('orders', 'special_instructions', 'TEXT'),
            ('orders', 'delivered_at',         'TIMESTAMP'),
            ('drivers', 'latitude',            'DOUBLE PRECISION'),
            ('drivers', 'longitude',           'DOUBLE PRECISION'),
            ('drivers', 'location_updated_at', 'TIMESTAMP'),
        ]
        for table, col, col_def in migrations:
            try:
                conn = self.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
                try:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}"
                    ))
                finally:
                    conn.close()
            except Exception:
                pass  # Column exists or other harmless issue

    # Delegate all methods to use SQL queries
    def get_orders(self):
        """Get all orders."""
        return pd.read_sql("SELECT * FROM orders ORDER BY created_at DESC", self.engine)

    def save_order(self, order_data, wms_response=None, pushed=False):
        """Save an order."""
        # Ensure all required fields have defaults if not provided
        if 'zone' not in order_data:
            order_data['zone'] = ''
        if 'driver_id' not in order_data:
            order_data['driver_id'] = ''
        if 'instructions' not in order_data:
            order_data['instructions'] = ''

        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO orders (
                    order_id, customer, email, phone, address, suburb, postcode, state,
                    parcels, service_level, status, zone, driver_id, instructions,
                    tracking_number, order_date, created_at, updated_at
                ) VALUES (
                    :order_id, :customer, :email, :phone, :address, :suburb, :postcode, :state,
                    :parcels, :service_level, :status, :zone, :driver_id, :instructions,
                    :tracking_number, :order_date, :created_at, :updated_at
                )
                ON CONFLICT (order_id) DO UPDATE SET
                    customer = EXCLUDED.customer,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    address = EXCLUDED.address,
                    suburb = EXCLUDED.suburb,
                    postcode = EXCLUDED.postcode,
                    state = EXCLUDED.state,
                    parcels = EXCLUDED.parcels,
                    service_level = EXCLUDED.service_level,
                    status = EXCLUDED.status,
                    zone = EXCLUDED.zone,
                    driver_id = EXCLUDED.driver_id,
                    instructions = EXCLUDED.instructions,
                    updated_at = CURRENT_TIMESTAMP
            """), order_data)
            conn.commit()

    def update_order_status(self, order_id, status, driver_id=None):
        """Update order status."""
        with self.engine.connect() as conn:
            if driver_id:
                conn.execute(text("""
                    UPDATE orders SET status = :status, driver_id = :driver_id, updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = :order_id
                """), {'order_id': order_id, 'status': status, 'driver_id': driver_id})
            else:
                conn.execute(text("""
                    UPDATE orders SET status = :status, updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = :order_id
                """), {'order_id': order_id, 'status': status})
            conn.commit()

    def update_order_fields(self, order_id, **fields):
        """Update order fields."""
        if not fields:
            return

        set_clause = ', '.join([f"{k} = :{k}" for k in fields.keys()])
        fields['order_id'] = order_id

        with self.engine.connect() as conn:
            conn.execute(text(f"""
                UPDATE orders SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = :order_id
            """), fields)
            conn.commit()

    def get_order_by_id(self, order_id):
        """Get order by ID."""
        result = pd.read_sql(
            "SELECT * FROM orders WHERE order_id = %(order_id)s",
            self.engine,
            params={'order_id': order_id}
        )
        # Return a plain dict (like local_store does) so callers can use .get()
        return result.iloc[0].to_dict() if not result.empty else None

    def get_order_by_tracking(self, tracking_number):
        """Get order by tracking number."""
        result = pd.read_sql(
            "SELECT * FROM orders WHERE tracking_number = %(tracking)s",
            self.engine,
            params={'tracking': tracking_number}
        )
        return result.iloc[0].to_dict() if not result.empty else None

    def tracking_number_exists(self, tracking_number):
        """Check if tracking number exists."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM orders WHERE tracking_number = :tracking
            """), {'tracking': tracking_number})
            return result.fetchone()[0] > 0

    # Drivers
    def get_drivers(self):
        """Get all drivers with calculated statistics."""
        drivers_df = pd.read_sql("SELECT * FROM drivers ORDER BY name", self.engine)

        if drivers_df.empty:
            return drivers_df

        today = datetime.now().strftime('%Y-%m-%d')

        # Single aggregation query replaces N+1 per-driver queries
        stats_df = pd.read_sql(
            """
            SELECT
                driver_id,
                SUM(CASE WHEN status IN ('allocated', 'in_transit') THEN 1 ELSE 0 END) AS active_orders,
                SUM(CASE WHEN status = 'delivered' AND created_at::date = %(today)s::date THEN 1 ELSE 0 END) AS deliveries_today,
                SUM(CASE WHEN status IN ('delivered', 'failed') THEN 1 ELSE 0 END) AS total_completed,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS total_delivered
            FROM orders
            WHERE driver_id IS NOT NULL
            GROUP BY driver_id
            """,
            self.engine,
            params={'today': today}
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

    def save_driver(self, driver_data):
        """Save a driver."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO drivers (
                    driver_id, name, vehicle_type, plate, status, current_zone, phone,
                    deliveries_today, success_rate, rating, active_orders, created_at
                ) VALUES (
                    :driver_id, :name, :vehicle_type, :plate, :status, :current_zone, :phone,
                    :deliveries_today, :success_rate, :rating, :active_orders, CURRENT_TIMESTAMP
                )
                ON CONFLICT (driver_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    vehicle_type = EXCLUDED.vehicle_type,
                    plate = EXCLUDED.plate,
                    status = EXCLUDED.status,
                    current_zone = EXCLUDED.current_zone,
                    phone = EXCLUDED.phone
            """), {
                'driver_id': driver_data['driver_id'],
                'name': driver_data['name'],
                'vehicle_type': driver_data.get('vehicle_type', 'Van'),
                'plate': driver_data.get('plate', ''),
                'status': driver_data.get('status', 'available'),
                'current_zone': driver_data.get('current_zone', ''),
                'phone': driver_data.get('phone', ''),
                'deliveries_today': driver_data.get('deliveries_today', 0),
                'success_rate': driver_data.get('success_rate', 0.95),
                'rating': driver_data.get('rating', 4.5),
                'active_orders': driver_data.get('active_orders', 0),
            })
            conn.commit()

    def update_driver(self, driver_id, driver_data):
        """Update driver."""
        fields = {k: v for k, v in driver_data.items()}
        fields['driver_id'] = driver_id

        set_clause = ', '.join([f"{k} = :{k}" for k in driver_data.keys()])

        with self.engine.connect() as conn:
            conn.execute(text(f"""
                UPDATE drivers SET {set_clause} WHERE driver_id = :driver_id
            """), fields)
            conn.commit()

    def delete_driver(self, driver_id):
        """Delete driver."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM drivers WHERE driver_id = :driver_id"), {'driver_id': driver_id})
            conn.commit()

    def update_driver_location(self, driver_id, latitude, longitude, timestamp=None):
        """Update driver's current location for real-time tracking."""
        from datetime import datetime as dt

        if timestamp is None:
            timestamp = dt.now().isoformat()

        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE drivers
                SET latitude = :latitude,
                    longitude = :longitude,
                    location_updated_at = :timestamp
                WHERE driver_id = :driver_id
            """), {
                'driver_id': driver_id,
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': timestamp
            })
            conn.commit()

    # Runs
    def get_runs(self):
        """Get all runs."""
        return pd.read_sql("SELECT * FROM runs ORDER BY created_at DESC", self.engine)

    def save_run(self, run_data):
        """Save a run."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO runs (
                    run_id, zone, driver_id, driver_name, status, total_stops, completed,
                    created_at, updated_at
                ) VALUES (
                    :run_id, :zone, :driver_id, :driver_name, :status, :total_stops, :completed,
                    :created_at, CURRENT_TIMESTAMP
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    zone = EXCLUDED.zone,
                    driver_id = EXCLUDED.driver_id,
                    driver_name = EXCLUDED.driver_name,
                    status = EXCLUDED.status,
                    total_stops = EXCLUDED.total_stops,
                    completed = EXCLUDED.completed,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                'run_id': run_data['run_id'],
                'zone': run_data.get('zone', ''),
                'driver_id': run_data.get('driver_id', ''),
                'driver_name': run_data.get('driver_name', ''),
                'status': run_data.get('status', 'active'),
                'total_stops': run_data.get('total_stops', 0),
                'completed': run_data.get('completed', 0),
                'created_at': run_data.get('created_at', datetime.now().isoformat()),
            })
            conn.commit()

    def save_run_orders(self, run_id, order_ids):
        """Save run orders."""
        with self.engine.connect() as conn:
            for seq, oid in enumerate(order_ids, 1):
                conn.execute(text("""
                    INSERT INTO run_orders (run_id, order_id, stop_sequence, status)
                    VALUES (:run_id, :order_id, :seq, 'pending')
                """), {'run_id': run_id, 'order_id': oid, 'seq': seq})
            conn.commit()

    def get_run_orders(self, run_id):
        """Get orders for a run."""
        return pd.read_sql(
            """
            SELECT o.* FROM orders o
            JOIN run_orders ro ON o.order_id = ro.order_id
            WHERE ro.run_id = :run_id
            ORDER BY ro.stop_sequence
            """,
            self.engine,
            params={'run_id': run_id}
        )

    def update_run_status(self, run_id, status):
        """Update run status."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE runs SET status = :status, updated_at = CURRENT_TIMESTAMP
                WHERE run_id = :run_id
            """), {'run_id': run_id, 'status': status})
            conn.commit()

    def update_run_progress(self, run_id, completed):
        """Update run progress."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE runs SET completed = :completed, updated_at = CURRENT_TIMESTAMP
                WHERE run_id = :run_id
            """), {'run_id': run_id, 'completed': completed})
            conn.commit()

    def count_runs_today(self):
        """Count runs created today."""
        today = datetime.now().strftime('%Y-%m-%d')
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM runs
                WHERE DATE(created_at) = :today
            """), {'today': today})
            return result.fetchone()[0]

    # Settings
    def get_setting(self, key, default=None):
        """Get a setting."""
        result = pd.read_sql(
            "SELECT value FROM settings WHERE key = %(key)s",
            self.engine,
            params={'key': key}
        )
        return result.iloc[0]['value'] if not result.empty else default

    def set_setting(self, key, value):
        """Set a setting."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (:key, :value, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """), {'key': key, 'value': value})
            conn.commit()

    def get_all_settings(self):
        """Get all settings."""
        result = pd.read_sql("SELECT key, value FROM settings", self.engine)
        return {row['key']: row['value'] for _, row in result.iterrows()}

    def set_settings_bulk(self, settings_dict):
        """Set multiple settings."""
        for key, value in settings_dict.items():
            self.set_setting(key, value)

    # Zones
    def get_zones(self):
        """Get all zones."""
        return pd.read_sql("SELECT * FROM zones ORDER BY zone_name", self.engine)

    def save_zone(self, zone_data):
        """Save a zone."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO zones (zone_name, suburbs, created_at)
                VALUES (:zone_name, :suburbs, CURRENT_TIMESTAMP)
                ON CONFLICT (zone_name) DO UPDATE SET
                    suburbs = EXCLUDED.suburbs
            """), zone_data)
            conn.commit()

    def delete_zone(self, zone_name):
        """Delete a zone."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM zones WHERE zone_name = :zone_name"), {'zone_name': zone_name})
            conn.commit()

    def seed_default_zones(self):
        """Seed default zones - only if zones table is empty."""
        zones_df = self.get_zones()
        if not zones_df.empty:
            return

        from config.constants import ZONE_MAPPING
        for zone_name, suburbs in ZONE_MAPPING.items():
            self.save_zone({
                'zone_name': zone_name,
                'suburbs': ','.join(suburbs)
            })

    # Admin authentication
    def get_admin_user(self, username):
        """Get admin user."""
        result = pd.read_sql(
            "SELECT * FROM admin_users WHERE username = %(username)s",
            self.engine,
            params={'username': username}
        )
        return result.iloc[0].to_dict() if not result.empty else None

    def create_admin_user(self, username, password_hash, salt):
        """Create admin user."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO admin_users (username, password_hash, salt, created_at)
                VALUES (:username, :password_hash, :salt, CURRENT_TIMESTAMP)
            """), {'username': username, 'password_hash': password_hash, 'salt': salt})
            conn.commit()

    def admin_user_count(self):
        """Count admin users."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as count FROM admin_users"))
            return result.fetchone()[0]

    # Session tokens
    def create_session_token(self, token, username, expires_at):
        """Create session token."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO session_tokens (token, username, expires_at, created_at)
                VALUES (:token, :username, :expires_at, CURRENT_TIMESTAMP)
            """), {'token': token, 'username': username, 'expires_at': expires_at})
            conn.commit()

    def get_session_token(self, token):
        """Get session token."""
        result = pd.read_sql(
            """
            SELECT * FROM session_tokens
            WHERE token = %(token)s AND expires_at > CURRENT_TIMESTAMP
            """,
            self.engine,
            params={'token': token}
        )
        return result.iloc[0].to_dict() if not result.empty else None

    def delete_session_token(self, token):
        """Delete session token."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM session_tokens WHERE token = :token"), {'token': token})
            conn.commit()

    # Driver auth tokens (DB-backed so they survive server restarts)
    def save_driver_token(self, token, driver_id, phone, expires_at):
        """Persist a driver auth token to the database."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO driver_tokens (token, driver_id, phone, expires_at)
                VALUES (:token, :driver_id, :phone, :expires_at)
                ON CONFLICT (token) DO NOTHING
            """), {'token': token, 'driver_id': driver_id, 'phone': phone, 'expires_at': expires_at})
            conn.commit()

    def get_driver_token(self, token):
        """Return token data if valid and not expired, else None."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT driver_id, phone, expires_at FROM driver_tokens
                WHERE token = :token AND expires_at > CURRENT_TIMESTAMP
            """), {'token': token})
            row = result.fetchone()
        if row is None:
            return None
        return {'driver_id': row[0], 'phone': row[1], 'expires': str(row[2])}

    def delete_driver_token(self, token):
        """Invalidate a driver token."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM driver_tokens WHERE token = :token"), {'token': token})
            conn.commit()

    def purge_expired_driver_tokens(self):
        """Remove expired tokens (called at login time to keep table lean)."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM driver_tokens WHERE expires_at <= CURRENT_TIMESTAMP"))
            conn.commit()

    # API log
    def log_api_call(self, operation, endpoint, request_summary, success, status_code=None, response_body=None, error_message=None):
        """Log API call."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO api_log (
                    timestamp, operation, endpoint, request_summary,
                    success, status_code, response_body, error_message
                ) VALUES (
                    CURRENT_TIMESTAMP, :operation, :endpoint, :request_summary,
                    :success, :status_code, :response_body, :error_message
                )
            """), {
                'operation': operation,
                'endpoint': endpoint,
                'request_summary': request_summary,
                'success': success,
                'status_code': status_code,
                'response_body': response_body,
                'error_message': error_message
            })
            conn.commit()

    def get_api_log(self):
        """Get API log."""
        return pd.read_sql("SELECT * FROM api_log ORDER BY timestamp DESC LIMIT 100", self.engine)

    def clear_api_log(self):
        """Clear API log."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM api_log"))
            conn.commit()

    # Receipts (WMS)
    def get_receipts(self):
        """Get all receipts."""
        return pd.read_sql("SELECT * FROM receipts ORDER BY created_at DESC", self.engine)

    def save_receipt(self, receipt_data, wms_response=None, pushed=False):
        """Save a receipt."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO receipts (
                    shipment_number, supplier, expected_date, status,
                    items_json, pushed, wms_response, created_at
                ) VALUES (
                    :shipment_number, :supplier, :expected_date, :status,
                    :items_json, :pushed, :wms_response, CURRENT_TIMESTAMP
                )
                ON CONFLICT (shipment_number) DO UPDATE SET
                    supplier = EXCLUDED.supplier,
                    expected_date = EXCLUDED.expected_date,
                    status = EXCLUDED.status,
                    items_json = EXCLUDED.items_json,
                    pushed = EXCLUDED.pushed,
                    wms_response = EXCLUDED.wms_response
            """), {
                'shipment_number': receipt_data['shipment_number'],
                'supplier': receipt_data.get('supplier', ''),
                'expected_date': receipt_data.get('expected_date', ''),
                'status': receipt_data.get('status', 'pending'),
                'items_json': receipt_data.get('items_json', '[]'),
                'pushed': pushed,
                'wms_response': str(wms_response) if wms_response else None
            })
            conn.commit()

    # Items
    def get_items(self):
        """Get all items."""
        return pd.read_sql("SELECT * FROM items ORDER BY created_at DESC", self.engine)

    def save_item(self, item_data, wms_response=None, pushed=False):
        """Save an item."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO items (
                    item_code, description, barcode, category, unit_of_measure,
                    pushed, wms_response, created_at
                ) VALUES (
                    :item_code, :description, :barcode, :category, :unit_of_measure,
                    :pushed, :wms_response, CURRENT_TIMESTAMP
                )
                ON CONFLICT (item_code) DO UPDATE SET
                    description = EXCLUDED.description,
                    barcode = EXCLUDED.barcode,
                    category = EXCLUDED.category,
                    unit_of_measure = EXCLUDED.unit_of_measure,
                    pushed = EXCLUDED.pushed,
                    wms_response = EXCLUDED.wms_response
            """), {
                'item_code': item_data['item_code'],
                'description': item_data.get('description', ''),
                'barcode': item_data.get('barcode', ''),
                'category': item_data.get('category', ''),
                'unit_of_measure': item_data.get('unit_of_measure', 'EA'),
                'pushed': pushed,
                'wms_response': str(wms_response) if wms_response else None
            })
            conn.commit()

    def delete_item(self, item_code):
        """Delete an item."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM items WHERE item_code = :item_code"), {'item_code': item_code})
            conn.commit()

    # === Messages ===

    def save_message(self, driver_id, driver_name, body, direction='inbound'):
        """Save a driver↔admin message. direction: 'inbound' = driver→admin, 'outbound' = admin→driver."""
        from datetime import datetime as dt, timezone
        sent_at = dt.now(timezone.utc).isoformat()
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO messages (driver_id, driver_name, body, direction, is_read, sent_at)
                VALUES (:driver_id, :driver_name, :body, :direction, FALSE, :sent_at)
                RETURNING id
            """), {
                'driver_id': driver_id,
                'driver_name': driver_name,
                'body': body,
                'direction': direction,
                'sent_at': sent_at,
            })
            row = result.fetchone()
            conn.commit()
        return row[0] if row else None

    def get_messages_for_driver(self, driver_id, limit=100):
        """Get all messages for a specific driver (conversation thread)."""
        result = pd.read_sql(
            "SELECT * FROM messages WHERE driver_id = %(driver_id)s ORDER BY sent_at ASC LIMIT %(limit)s",
            self.engine,
            params={'driver_id': driver_id, 'limit': limit},
        )
        return result.to_dict('records')

    def get_unread_count(self, driver_id=None):
        """Count unread outbound messages (admin→driver) for a driver."""
        with self.engine.connect() as conn:
            if driver_id:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM messages
                    WHERE driver_id=:driver_id AND direction='outbound' AND is_read=FALSE
                """), {'driver_id': driver_id})
            else:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM messages WHERE direction='outbound' AND is_read=FALSE
                """))
            return result.fetchone()[0]

    def mark_messages_read(self, driver_id):
        """Mark all outbound messages to a driver as read (driver has seen them)."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE messages SET is_read=TRUE
                WHERE driver_id=:driver_id AND direction='outbound'
            """), {'driver_id': driver_id})
            conn.commit()
