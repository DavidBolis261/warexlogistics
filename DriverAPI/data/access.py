"""Account isolation and driver credentials, shared by the web and API services."""
import hashlib
import hmac
import secrets
import time
import pandas as pd
from sqlalchemy import text


class AccessStore:
    def __init__(self, store):
        self.store = store
        self.execute('CREATE TABLE IF NOT EXISTS partner_accounts (username TEXT PRIMARY KEY, approved INTEGER DEFAULT 0)')
        self.execute('CREATE TABLE IF NOT EXISTS partner_orders (order_id TEXT PRIMARY KEY, username TEXT NOT NULL)')
        self.execute('CREATE TABLE IF NOT EXISTS driver_credentials (driver_id TEXT PRIMARY KEY, password_hash TEXT NOT NULL, failures INTEGER DEFAULT 0, locked_until BIGINT DEFAULT 0)')

    def execute(self, sql, params=None, read=False):
        params = params or {}
        if hasattr(self.store, 'engine'):
            with self.store.engine.begin() as conn:
                result = conn.execute(text(sql), params)
                return [dict(row) for row in result.mappings()] if read else None
        result = self.store.conn.execute(sql, params)
        if read:
            return [dict(row) for row in result.fetchall()]
        self.store.conn.commit()

    def partners(self):
        return self.execute("SELECT a.username, a.company_name, COALESCE(p.approved, 0) AS approved FROM admin_users a LEFT JOIN partner_accounts p ON p.username=a.username WHERE a.role='client' ORDER BY a.username", read=True)

    def approved(self, username):
        rows = self.execute('SELECT approved FROM partner_accounts WHERE username=:username', {'username':username}, True)
        return bool(rows and rows[0]['approved'])

    def approve(self, username, approved):
        self.execute('INSERT INTO partner_accounts(username, approved) VALUES (:username,:approved) ON CONFLICT(username) DO UPDATE SET approved=excluded.approved', {'username':username, 'approved':int(approved)})

    def assign(self, username, order_ids):
        # Each order belongs to one explicitly selected partner account.
        for order_id in order_ids:
            self.execute('INSERT INTO partner_orders(order_id, username) VALUES (:id,:username) ON CONFLICT(order_id) DO UPDATE SET username=excluded.username', {'id':order_id,'username':username})

    def partner_orders(self, token):
        session = self.store.get_session_token(token)
        if not session or not self.approved(session['username']):
            return pd.DataFrame()
        return pd.DataFrame(self.execute('SELECT o.* FROM orders o JOIN partner_orders p ON p.order_id=o.order_id WHERE p.username=:username ORDER BY o.created_at DESC', {'username':session['username']}, True))

    def set_driver_password(self, driver_id, password):
        if len(password) < 12:
            raise ValueError('Use a password of at least 12 characters.')
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
        self.execute('INSERT INTO driver_credentials(driver_id,password_hash) VALUES (:id,:hash) ON CONFLICT(driver_id) DO UPDATE SET password_hash=excluded.password_hash, failures=0, locked_until=0', {'id':driver_id,'hash':salt+':'+digest})
        self.execute('DELETE FROM driver_tokens WHERE driver_id=:id', {'id':driver_id})

    def verify_driver(self, driver_id, password):
        rows = self.execute('SELECT * FROM driver_credentials WHERE driver_id=:id', {'id':driver_id}, True)
        if not rows or rows[0]['locked_until'] > time.time():
            return False
        row = rows[0]
        salt, digest = row['password_hash'].split(':',1)
        candidate = hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
        if not hmac.compare_digest(digest,candidate):
            self.execute('UPDATE driver_credentials SET failures=failures+1, locked_until=CASE WHEN failures>=4 THEN :until ELSE locked_until END WHERE driver_id=:id', {'until':int(time.time())+900,'id':driver_id})
            return False
        self.execute('UPDATE driver_credentials SET failures=0, locked_until=0 WHERE driver_id=:id', {'id':driver_id})
        return True
