"""Opt-in worker; each thread owns its database connection. No secrets in logs."""
import logging
import os
import threading
from datetime import datetime, timezone
from integrations.starshipit import StarshipitClient, StarshipitSync, StarshipitError


def start_worker():
    if os.getenv('STARSHIPIT_SYNC_ENABLED','false').lower() != 'true' or not StarshipitClient().configured:
        return
    def run():
        from data.data_manager import DataManager
        try:interval=max(60,int(os.getenv('STARSHIPIT_SYNC_INTERVAL_SECONDS','300')))
        except ValueError:interval=300
        while True:
            dm=None
            try:
                dm=DataManager();sync=StarshipitSync(dm)
                sync.save_setting('heartbeat',datetime.now(timezone.utc).isoformat())
                if sync.setting('auto_import','false')=='true':
                    try:sync.import_recent()
                    except StarshipitError as exc:sync.save_setting('last_error',str(exc))
                sync.flush()
            except StarshipitError as exc:
                logging.warning('Starshipit worker: %s',exc)
            except Exception:
                logging.error('Starshipit worker encountered a database or processing error; will retry.')
            finally:
                if dm is not None:
                    if hasattr(dm.store,'engine'):dm.store.engine.dispose()
                    elif hasattr(dm.store,'conn'):dm.store.conn.close()
            threading.Event().wait(interval)
    threading.Thread(target=run,name='starshipit-sync',daemon=True).start()
