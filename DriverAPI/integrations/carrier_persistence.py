"""Isolated carrier UAT persistence. Migration is explicit, never startup DDL."""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import MetaData, Table, Column, Text, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from api.carrier_preview import Conflict, UATStore

metadata = MetaData()
orders = Table('carrier_uat_orders', metadata,
    Column('partner', Text, primary_key=True),
    Column('request_key', Text, primary_key=True),
    Column('digest', Text, nullable=False),
    Column('tracking', Text, nullable=False, unique=True),
    Column('payload', Text, nullable=False))


def migrate_carrier_uat(engine):
    """Explicit additive migration; caller must separately approve production execution."""
    metadata.create_all(engine)


class SQLAlchemyUATStore:
    def __init__(self, engine):
        if engine.dialect.name not in ('postgresql', 'sqlite'):
            raise ValueError('Unsupported UAT database dialect.')
        self.engine = engine

    def check_schema(self):
        with self.engine.connect() as conn:
            conn.execute(select(orders).limit(0))

    @staticmethod
    def _decode(row, payload):
        if row is None:
            return None
        if row.digest != UATStore.digest(payload):
            raise Conflict('Idempotency key already used with different input.')
        return row.tracking, json.loads(row.payload)

    def replay(self, partner, key, payload):
        with self.engine.connect() as conn:
            row = conn.execute(select(orders).where(
                orders.c.partner == partner, orders.c.request_key == key)).first()
            return self._decode(row, payload)

    def create(self, partner, key, payload, rate):
        tracking = 'UAT-' + uuid.uuid4().hex.upper()
        record = dict(request=payload, rate=rate, created_at=datetime.now(timezone.utc).isoformat())
        insert = pg_insert if self.engine.dialect.name == 'postgresql' else sqlite_insert
        statement = insert(orders).values(partner=partner, request_key=key,
            digest=UATStore.digest(payload), tracking=tracking,
            payload=json.dumps(record, sort_keys=True, allow_nan=False)).on_conflict_do_nothing(
                index_elements=['partner', 'request_key']).returning(orders.c.tracking)
        with self.engine.begin() as conn:
            created = conn.execute(statement).first() is not None
            # In PostgreSQL READ COMMITTED this statement sees the winning insert
            # after ON CONFLICT waits for its transaction. Conflicts never overwrite.
            row = conn.execute(select(orders).where(
                orders.c.partner == partner, orders.c.request_key == key)).first()
            prior = self._decode(row, payload)
            if prior is None:
                raise RuntimeError('UAT persistence did not return a stored record.')
            return prior[0], prior[1], not created

    def get(self, partner, tracking):
        with self.engine.connect() as conn:
            row = conn.execute(select(orders.c.payload).where(
                orders.c.partner == partner, orders.c.tracking == tracking)).first()
        return json.loads(row.payload) if row else None
