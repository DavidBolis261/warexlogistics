"""Starshipit order import and durable writeback. Shared verbatim by both services."""
import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import requests

API_URL = 'https://api.starshipit.com/api'


class StarshipitError(Exception):
    def __init__(self, message, retry_after=60, permanent=False):
        super().__init__(message)
        self.retry_after = retry_after
        self.permanent = permanent


class StarshipitClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.last_request = 0

    @property
    def configured(self):
        return bool(os.getenv('STARSHIPIT_API_KEY') and os.getenv('STARSHIPIT_SUBSCRIPTION_KEY'))

    def request(self, method, path, **kwargs):
        if not self.configured:
            raise StarshipitError('Add both Starshipit credentials in Railway first.', permanent=True)
        # One request per second: below the documented developer limit of two.
        time.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        try:
            response = self.session.request(method, API_URL + path, headers={
                'StarShipIT-Api-Key': os.environ['STARSHIPIT_API_KEY'],
                'Ocp-Apim-Subscription-Key': os.environ['STARSHIPIT_SUBSCRIPTION_KEY'],
                'Content-Type': 'application/json',
            }, timeout=(10, 30), allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise StarshipitError('Starshipit could not be reached. The operation can be retried.') from None
        if response.status_code == 429:
            try:
                delay = max(60, min(86400, int(response.headers.get('Retry-After', 60))))
            except (ValueError, TypeError):
                delay = 60
            raise StarshipitError('Starshipit rate limit reached. Waiting before retry.', delay)
        if response.status_code in (401, 403):
            raise StarshipitError('Starshipit rejected the credentials or account permissions.', permanent=True)
        if not 200 <= response.status_code < 300:
            raise StarshipitError(f'Starshipit returned HTTP {response.status_code}.', permanent=response.status_code < 500)
        try:
            data = response.json()
        except ValueError:
            raise StarshipitError('Starshipit returned an invalid JSON response.') from None
        if not isinstance(data, dict) or (data.get('success') is not True and data.get('succeeded') is not True):
            # Provider error bodies may contain addresses or credentials. Do not persist them.
            raise StarshipitError('Starshipit rejected the request. Review its order state and account permissions.', permanent=True)
        return data

    def get_order(self, remote_id):
        data = self.request('GET', '/orders', params={'order_id': int(remote_id), 'include': ['Sender_Details','Destination','Items','Packages','Metadatas']})
        order = data.get('order')
        if isinstance(order, list):
            order = order[0] if len(order) == 1 else None
        if order is None:
            rows = data.get('data', {}).get('orders', data.get('orders', []))
            order = rows[0] if len(rows) == 1 else None
        if not isinstance(order, dict) or str(order.get('order_id')) != str(remote_id):
            raise StarshipitError('Starshipit did not return the requested order.', permanent=True)
        return order

    def list_orders(self, status, since, page=1):
        if status not in ('unshipped', 'shipped', 'printed'):
            raise ValueError('Unsupported import status')
        path = '/orders/shipments' if status == 'printed' else '/orders/' + status
        params = {'limit': 250, 'page': page}
        if status == 'printed':
            params.update(status='recently_printed', since_created_date=since)
        else:
            params['since_last_updated'] = since
        data = self.request('GET', path, params=params)
        if not isinstance(data.get('orders'), list):
            raise StarshipitError('Starshipit returned an unexpected order list.')
        return data


class StarshipitSync:
    def __init__(self, dm, client=None):
        self.dm = dm
        self.db = dm.access
        self.client = client or StarshipitClient()
        self.account = os.getenv('STARSHIPIT_ACCOUNT', 'primary').strip() or 'primary'
        self.db.execute('''CREATE TABLE IF NOT EXISTS starshipit_orders (
            account TEXT NOT NULL, remote_id TEXT NOT NULL, local_id TEXT NOT NULL UNIQUE,
            order_number TEXT, remote_status TEXT, snapshot TEXT, imported_at TEXT,
            last_sent_status TEXT, last_sent_at TEXT,
            PRIMARY KEY(account, remote_id))''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS starshipit_jobs (
            account TEXT NOT NULL, local_id TEXT NOT NULL, kind TEXT NOT NULL,
            payload TEXT NOT NULL, version TEXT NOT NULL, state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, retry_at BIGINT NOT NULL DEFAULT 0,
            error TEXT, updated_at TEXT, PRIMARY KEY(account, local_id, kind))''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS starshipit_locks (
            account TEXT PRIMARY KEY, owner TEXT NOT NULL, expires BIGINT NOT NULL)''')

    @contextmanager
    def lock(self):
        owner = uuid.uuid4().hex
        self.db.execute('''INSERT INTO starshipit_locks(account,owner,expires) VALUES (:a,:o,:e)
            ON CONFLICT(account) DO UPDATE SET owner=excluded.owner, expires=excluded.expires
            WHERE starshipit_locks.expires < :now''', {'a': self.account,'o':owner,'e':int(time.time())+1800,'now':int(time.time())})
        row = self.db.execute('SELECT owner FROM starshipit_locks WHERE account=:a', {'a':self.account}, True)[0]
        if row['owner'] != owner:
            raise StarshipitError('Another Starshipit sync is running. Try again shortly.')
        self._lock_owner = owner
        try:
            yield
        finally:
            self._lock_owner = None
            self.db.execute('DELETE FROM starshipit_locks WHERE account=:a AND owner=:o', {'a':self.account,'o':owner})

    def renew_lock(self):
        owner = getattr(self, '_lock_owner', None)
        if owner:
            row = self.db.execute('SELECT owner FROM starshipit_locks WHERE account=:a', {'a':self.account}, True)
            if not row or row[0]['owner'] != owner:
                raise StarshipitError('Sync lease expired. Retry this operation.')
            self.db.execute('UPDATE starshipit_locks SET expires=:e WHERE account=:a AND owner=:o', {'e':int(time.time())+1800,'a':self.account,'o':owner})

    def setting(self, key, default=''):
        return self.dm.store.get_setting('starshipit_'+self.account+'_'+key, default)

    def save_setting(self, key, value):
        self.dm.store.set_setting('starshipit_'+self.account+'_'+key, str(value))

    def links(self):
        return self.db.execute('SELECT account,remote_id,local_id,order_number,remote_status,imported_at,last_sent_status,last_sent_at FROM starshipit_orders WHERE account=:a ORDER BY imported_at DESC', {'a':self.account}, True)

    def jobs(self):
        return self.db.execute('SELECT local_id,kind,state,attempts,error,updated_at FROM starshipit_jobs WHERE account=:a ORDER BY updated_at DESC', {'a':self.account}, True)

    def _link(self, local_id):
        rows = self.db.execute('SELECT * FROM starshipit_orders WHERE account=:a AND local_id=:id', {'a':self.account,'id':local_id}, True)
        return rows[0] if rows else None

    def import_order(self, remote):
        self.renew_lock()
        remote_id = str(remote.get('order_id', ''))
        if not remote_id.isdigit() or int(remote_id) <= 0:
            raise StarshipitError('An order has no valid Starshipit ID.', permanent=True)
        destination = remote.get('destination') or {}
        if not destination.get('street') or not destination.get('name'):
            raise StarshipitError(f'Order {remote_id} needs a recipient and delivery address.', permanent=True)
        if remote.get('archived') or remote.get('type', 'Outgoing').lower() != 'outgoing':
            return 'skipped'
        local_id = 'SSI-' + hashlib.sha256(self.account.encode()).hexdigest()[:8] + '-' + remote_id
        now = datetime.now(timezone.utc).isoformat()
        status = str(remote.get('status') or remote.get('order_status') or 'Unshipped')
        fields = {
            'customer':destination['name'], 'address':destination['street'],
            'suburb':destination.get('suburb') or destination.get('city') or '',
            'state':destination.get('state') or '', 'postcode':destination.get('post_code') or '',
            'email':destination.get('email') or '', 'phone':destination.get('phone') or '',
            'address2':destination.get('building') or '', 'delivery_company':destination.get('company') or '',
            'country':destination.get('country') or 'Australia',
            'special_instructions':destination.get('delivery_instructions') or '',
            'pickup_address':(remote.get('sender_details') or {}).get('street') or '',
            'pickup_suburb':(remote.get('sender_details') or {}).get('suburb') or '',
            'pickup_state':(remote.get('sender_details') or {}).get('state') or '',
            'pickup_postcode':(remote.get('sender_details') or {}).get('post_code') or '',
            'pickup_contact':(remote.get('sender_details') or {}).get('name') or '',
            'pickup_phone':(remote.get('sender_details') or {}).get('phone') or '',
            'parcels':max(1,len(remote.get('packages') or [])),
        }
        current = self.dm.store.get_order_by_id(local_id)
        if current is None:
            data = dict(fields, order_id=local_id, tracking_number=local_id, status='delivered' if status.lower()=='delivered' else 'pending',
                        driver_id='', zone='', service_level='standard', created_at=remote.get('order_date') or now,
                        updated_at=now, order_date=str(remote.get('order_date') or now)[:10], weight=None,
                        instructions=destination.get('delivery_instructions') or '')
            self.dm.store.save_order(data)
            self.dm.store.update_order_fields(local_id, **fields)
            outcome = 'imported'
        elif current.get('status') == 'pending' and not current.get('driver_id') and not self.db.execute("SELECT 1 FROM starshipit_jobs WHERE account=:a AND local_id=:id AND kind='details' AND state<>'done'", {'a':self.account,'id':local_id}, True):
            self.dm.store.update_order_fields(local_id, **fields)
            outcome = 'refreshed'
        else:
            # Warex owns dispatch, delivery outcomes, notes and evidence after allocation.
            outcome = 'preserved'
        self.db.execute('''INSERT INTO starshipit_orders(account,remote_id,local_id,order_number,remote_status,snapshot,imported_at)
            VALUES (:a,:r,:l,:n,:s,:p,:t) ON CONFLICT(account,remote_id) DO UPDATE SET
            order_number=excluded.order_number, remote_status=excluded.remote_status,
            snapshot=excluded.snapshot, imported_at=excluded.imported_at''',
            {'a':self.account,'r':remote_id,'l':local_id,'n':str(remote.get('order_number') or ''),'s':status,'p':json.dumps(remote),'t':now})
        return outcome

    def import_recent(self, since=None, statuses=None):
        statuses = statuses or json.loads(self.setting('statuses', '["unshipped"]'))
        since = since or self.setting('cursor') or (datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
        started = datetime.now(timezone.utc)-timedelta(minutes=5)
        carrier = self.setting('carrier').strip().lower()
        if not carrier and self.setting('all_carriers','false') != 'true':
            raise StarshipitError('Choose a carrier filter or explicitly include all carriers first.', permanent=True)
        counts = dict(imported=0, refreshed=0, preserved=0, skipped=0)
        with self.lock():
            for status in statuses:
                for page in range(1, 101):
                    self.renew_lock()
                    data = self.client.list_orders(status, since, page)
                    for remote in data['orders']:
                        if not isinstance(remote, dict):
                            raise StarshipitError('Unexpected Starshipit order format.')
                        if carrier and carrier not in (str(remote.get('carrier') or '').lower(), str(remote.get('carrier_name') or '').lower()):
                            counts['skipped'] += 1
                            continue
                        if not remote.get('destination'):
                            remote = self.client.get_order(remote['order_id'])
                        counts[self.import_order(remote)] += 1
                    if page >= int(data.get('total_pages') or 1):
                        break
                else:
                    raise StarshipitError('Import exceeded 100 pages. Use a narrower date range; the cursor has not advanced.')
            self.save_setting('cursor', started.isoformat())
            self.save_setting('last_import', datetime.now(timezone.utc).isoformat())
            self.save_setting('last_error','')
        return counts

    def queue(self, local_id, kind, payload):
        if not self._link(local_id):
            return
        self.db.execute('''INSERT INTO starshipit_jobs(account,local_id,kind,payload,version,state,attempts,retry_at,error,updated_at)
            VALUES (:a,:id,:k,:p,:v,'queued',0,0,'',:t) ON CONFLICT(account,local_id,kind) DO UPDATE SET
            payload=excluded.payload,version=excluded.version,state='queued',attempts=0,retry_at=0,error='',updated_at=excluded.updated_at''',
            {'a':self.account,'id':local_id,'k':kind,'p':json.dumps(payload),'v':uuid.uuid4().hex,'t':datetime.now(timezone.utc).isoformat()})

    def reconcile_deliveries(self):
        rows = self.db.execute('''SELECT s.local_id,s.remote_id FROM starshipit_orders s JOIN orders o ON o.order_id=s.local_id
            WHERE s.account=:a AND o.status='delivered' AND COALESCE(s.last_sent_status,'')<>'Delivered'
            AND LOWER(s.remote_status)<>'delivered' AND NOT EXISTS
            (SELECT 1 FROM starshipit_jobs j WHERE j.account=s.account AND j.local_id=s.local_id AND j.kind='delivery' AND j.state<>'done')''', {'a':self.account}, True)
        for row in rows:
            self.queue(row['local_id'],'delivery',{'order_id':int(row['remote_id']),'status':'Delivered'})

    def details_payload(self, local_id):
        link = self._link(local_id)
        if not link:
            raise StarshipitError('This order is not linked to Starshipit.', permanent=True)
        local = self.dm.store.get_order_by_id(local_id)
        remote = json.loads(link['snapshot'])
        destination = {}
        destination.update(name=local['customer'], street=local['address'], suburb=local.get('suburb') or '',
                           state=local.get('state') or '',post_code=local.get('postcode') or '',
                           email=local.get('email') or '',phone=local.get('phone') or '',
                           building=local.get('address2') or '', company=local.get('delivery_company') or '',
                           country=local.get('country') or (remote.get('destination') or {}).get('country') or 'Australia',
                           delivery_instructions=local.get('special_instructions') or '')
        return {'order_id':int(link['remote_id']),'destination':destination}

    def retry(self):
        self.db.execute("UPDATE starshipit_jobs SET state='queued',retry_at=0 WHERE account=:a AND state IN ('blocked','retry')", {'a':self.account})

    def flush(self, limit=25):
        self.reconcile_deliveries()
        if not self.client.configured:
            return {'sent':0,'waiting':'credentials'}
        sent = 0
        with self.lock():
            rows = self.db.execute("SELECT * FROM starshipit_jobs WHERE account=:a AND state IN ('queued','retry') AND retry_at<=:now ORDER BY updated_at LIMIT :limit", {'a':self.account,'now':int(time.time()),'limit':limit}, True)
            for job in rows:
                self.renew_lock()
                try:
                    payload = json.loads(job['payload'])
                    if job['kind']=='delivery':
                        local = self.dm.store.get_order_by_id(job['local_id'])
                        if not local or local.get('status') != 'delivered':
                            raise StarshipitError('Delivery was changed locally. Review before retrying.', permanent=True)
                    elif job['kind']=='details':
                        remote = self.client.get_order(payload['order_id'])
                        if str(remote.get('status') or remote.get('order_status')).lower() not in ('unshipped','saved'):
                            raise StarshipitError('Address updates are restricted after Starshipit prints a label.', permanent=True)
                        destination = dict(remote.get('destination') or {})
                        destination.update(payload['destination'])
                        payload['destination'] = destination
                    self.client.request('PUT','/orders',json={'order':payload})
                    state,error,retry_at='done','',0
                    sent += 1
                    self.db.execute('''UPDATE starshipit_orders SET last_sent_at=:t,
                        last_sent_status=CASE WHEN :kind='delivery' THEN 'Delivered' ELSE last_sent_status END
                        WHERE account=:a AND local_id=:id''', {'t':datetime.now(timezone.utc).isoformat(),'kind':job['kind'],'a':self.account,'id':job['local_id']})
                except StarshipitError as exc:
                    state='blocked' if exc.permanent else 'retry'
                    error=str(exc)
                    retry_at=int(time.time())+max(exc.retry_after,min(3600,60*2**min(job['attempts'],6)))
                self.db.execute('''UPDATE starshipit_jobs SET state=:s,error=:e,retry_at=:r,attempts=attempts+1,updated_at=:t
                    WHERE account=:a AND local_id=:id AND kind=:k AND version=:v''',
                    {'s':state,'e':error,'r':retry_at,'t':datetime.now(timezone.utc).isoformat(),'a':self.account,'id':job['local_id'],'k':job['kind'],'v':job['version']})
        return {'sent':sent}
