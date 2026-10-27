"""Inactive same-service carrier UAT routes; no operational order dependencies.

Registration is disabled by default in the server. Identity is server-resolved. All stored records are UAT-only, with no
operational status transitions, notification, WMS, push or dispatch capability.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import sqlite3
from threading import RLock
import uuid

from flask import Blueprint, jsonify, request, Response
from integrations.draft_rates import calculate_rate, normalise_rate_request
from integrations.carrier_labels import parcel_ids, render_test_labels


@dataclass(frozen=True)
class TestIdentity:
    partner_id: str
    test_access: bool = False


class Conflict(ValueError):
    pass


class UATStore:
    """Local SQLite adapter for isolated UAT tables; not a live DB migration.

    The production store adapter/permissions must be reviewed before registration.
    No inserts into orders/runs/drivers tables occur. An atomic unique partner/key
    transaction enforces idempotency across connections and restarts.
    """
    def __init__(self, connection):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('A dedicated SQLite UAT connection is required.')
        self.db=connection;self.lock=RLock()
        self.db.execute('''CREATE TABLE IF NOT EXISTS carrier_uat_orders (
            partner TEXT NOT NULL, request_key TEXT NOT NULL,
            digest TEXT NOT NULL, tracking TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL, PRIMARY KEY(partner,request_key))''')
        self.db.commit()

    @staticmethod
    def digest(payload):
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def replay(self,partner,key,payload):
        with self.lock:
            row=self.db.execute('SELECT digest,tracking,payload FROM carrier_uat_orders WHERE partner=? AND request_key=?',
                                (partner,key)).fetchone()
        if row is None:return None
        if row[0] != self.digest(payload):
            raise Conflict('Idempotency key already used with different input.')
        return row[1],json.loads(row[2])

    def create(self,partner,key,payload,rate):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                prior=self.replay(partner,key,payload)
                if prior:
                    tracking,record=prior; replayed=True
                else:
                    tracking='UAT-'+uuid.uuid4().hex.upper();replayed=False
                    record={'request':payload,'rate':rate,'created_at':datetime.now(timezone.utc).isoformat()}
                    self.db.execute('INSERT INTO carrier_uat_orders VALUES (?,?,?,?,?)',
                        (partner,key,self.digest(payload),tracking,json.dumps(record,sort_keys=True,allow_nan=False)))
                self.db.commit();return tracking,record,replayed
            except Exception:
                self.db.rollback();raise

    def get(self,partner,tracking):
        with self.lock:
            row=self.db.execute('SELECT payload FROM carrier_uat_orders WHERE partner=? AND tracking=?',
                                (partner,tracking)).fetchone()
        return json.loads(row[0]) if row else None


def normalise_order(body):
    if not isinstance(body,dict) or set(body)-{'origin','destination','parcels','sender','recipient','instructions','reference'}:
        raise ValueError('Invalid order fields; identity and test mode are server-controlled.')
    normal=normalise_rate_request({key:body.get(key) for key in ('origin','destination','parcels')})
    for group,required in [('sender',{'name','address'}),('recipient',{'name','address','email','phone'})]:
        fields=body.get(group)
        if not isinstance(fields,dict) or set(fields)-required-{'address2'} or not required.issubset(fields):
            raise ValueError('Invalid '+group+' fields.')
        if any(not isinstance(v,str) or not v.strip() or len(v)>250 for v in fields.values()):
            raise ValueError(group+' fields must be non-empty strings of at most 250 characters.')
        normal[group]={k:v.strip() for k,v in fields.items()}
    for field in ('instructions','reference'):
        value=body.get(field,'')
        if not isinstance(value,str) or len(value)>250:
            raise ValueError(field+' must be a string of at most 250 characters.')
        normal[field]=value.strip()
    return normal


def rate_body(order):
    return {key:order[key] for key in ('origin','destination','parcels')}


def order_response(tracking,record,replayed=False):
    return {'success':True,'test':True,'status':'test_pending','tracking_number':tracking,
            'parcel_ids':parcel_ids(tracking,len(record['request']['parcels'])),
            'created_at':record['created_at'],'rate':record['rate'],'replayed':replayed}


def create_carrier_preview_blueprint(resolve_identity,store,coverage=None,label_renderer=render_test_labels):
    """Factory only. No key issuance, automatic registration or live configuration.

    resolve_identity must use trusted server-side access records. coverage is an
    approved CoveragePolicy, never supplied by clients. None blocks quote offers.
    """
    bp=Blueprint('carrier_preview',__name__)

    def guarded(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            identity=resolve_identity(request)
            if not isinstance(identity,TestIdentity) or not identity.partner_id or not identity.test_access:
                return jsonify(error='Authorised test access required.'),403
            if request.content_length is not None and request.content_length>65536:
                return jsonify(error='Request exceeds 64 KiB.'),413
            return fn(identity,*args,**kwargs)
        return wrapped

    def quote_status(result):
        if 'origin_or_destination_outside_configured_coverage' in result['unresolved_rules']:return 422
        return 200 if result['quote_ready'] else 409

    @bp.post('/api/v1/uat/rates')
    @guarded
    def rates(identity):
        try:result=calculate_rate(request.get_json(silent=True),coverage)
        except ValueError as exc:return jsonify(error=str(exc)),400
        result['test']=True
        return jsonify(result),quote_status(result)

    @bp.post('/api/v1/uat/orders')
    @guarded
    def create(identity):
        try:body=normalise_order(request.get_json(silent=True))
        except ValueError as exc:return jsonify(error=str(exc)),400
        key=request.headers.get('Idempotency-Key','')
        if not key or len(key)>128 or not key.isascii() or any(ord(c)<33 or ord(c)>126 for c in key):
            return jsonify(error='A printable Idempotency-Key of 1-128 characters is required.'),400
        try:
            prior=store.replay(identity.partner_id,key,body)
            if prior:return jsonify(order_response(*prior,replayed=True)),200
            rate=calculate_rate(rate_body(body),coverage)
            if not rate['quote_ready']:
                return jsonify(error='Shipment is not quotable.',test=True,rate=rate),quote_status(rate)
            tracking,record,replayed=store.create(identity.partner_id,key,body,rate)
        except Conflict as exc:return jsonify(error=str(exc)),409
        return jsonify(order_response(tracking,record,replayed)),200 if replayed else 201

    @bp.get('/api/v1/uat/orders/<tracking>')
    @guarded
    def get_order(identity,tracking):
        record=store.get(identity.partner_id,tracking)
        if record is None:return jsonify(error='Test order not found.'),404
        return jsonify(order_response(tracking,record))

    @bp.get('/api/v1/uat/orders/<tracking>/track')
    @guarded
    def track(identity,tracking):
        record=store.get(identity.partner_id,tracking)
        if record is None:return jsonify(error='Test order not found.'),404
        return jsonify(test=True,tracking_number=tracking,current_status='test_pending',
                       events=[{'status':'test_pending','occurred_at':record['created_at'],'description':'Test order recorded; no live delivery.'}])

    @bp.get('/api/v1/uat/orders/<tracking>/label')
    @guarded
    def label(identity,tracking):
        record=store.get(identity.partner_id,tracking)
        if record is None:return jsonify(error='Test order not found.'),404
        output_format=request.args.get('format','pdf')
        if set(request.args)-{'format'} or output_format not in ('pdf','html'):
            return jsonify(error='Supported formats: pdf, html.'),400
        if label_renderer is None:return jsonify(error='Label renderer is unavailable.'),503
        try:content=label_renderer(record['request'],tracking,output_format)
        except ImportError:return jsonify(error='Label renderer dependencies are unavailable.'),503
        except ValueError as exc:return jsonify(error=str(exc)),422
        return Response(content,mimetype='application/pdf' if output_format=='pdf' else 'text/html',headers={
            'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Content-Disposition':'attachment; filename="uat-labels.'+output_format+'"',
            'Content-Security-Policy':"default-src 'none'; img-src data:; style-src 'unsafe-inline'"})

    @bp.after_request
    def no_cache(response):
        response.headers['Cache-Control']='no-store';return response

    return bp
