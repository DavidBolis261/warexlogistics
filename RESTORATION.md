# Warex Railway restoration

Railway project: Warex Logistics. The Dashboard and DriverAPI share the Postgres service through `DATABASE_URL=${{Postgres.DATABASE_URL}}`.

Deployment settings are managed in Railway. Legacy conflicting railway.json/toml files have been removed.

| Service | Root | Start | Health | Port |
| --- | --- | --- | --- | --- |
| Dashboard | /WebPlatform | bash start.sh | /_stcore/health | 8501 |
| DriverAPI | /DriverAPI | gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 driver_api_server:app | /health | 5000 |

Both use Railpack and Python 3.12. Set SITE_DOMAIN=app.warexlogistics.com.au, TZ=Australia/Sydney, RESEND_API_KEY and EMAIL_FROM_ADDRESS on both services. Credentials belong only in Railway variables.

The first administrator must supply ADMIN_SETUP_TOKEN from the protected local handover file, then choose a username and password. The setup screen disappears once an administrator exists. Remove ADMIN_SETUP_TOKEN after setup. Never set RESET_ADMIN in production.

## Restored access and pages

Partner registration is available with `ALLOW_PARTNER_REGISTRATION=true` on Dashboard. New accounts wait for approval in **Partners**. An administrator explicitly assigns orders to each account; company-name matches never grant access. Suspending an account removes portal access immediately.

Driver login uses phone + a password of at least 12 characters, configured in **Driver Access**. Set `ENABLE_DRIVER_LOGIN=true` on DriverAPI and `DRIVER_API_URL=https://driverapi-production-b594.up.railway.app` on Dashboard. Password changes revoke existing driver sessions. Five unsuccessful password attempts lock the account for 15 minutes. The browser portal supports assigned deliveries, status updates, photo/signature uploads and messages. A restored iOS app must adopt this password login contract.

Dashboard navigation includes Driver Tracking (live positions/history), Delivery Evidence, Partners, Driver Access, Inventory and Integrations, alongside the existing operational pages. Orders includes All Orders. Settings includes routing preferences. Maximum stops is enforced when creating a run; duration, toll and express preferences are dispatch guidance, not automatic route optimization.

## Remaining provider configuration

| Feature | Variables / setup | Service |
| --- | --- | --- |
| Address suggestions | `GOOGLE_PLACES_API_KEY` with Places access | Dashboard |
| Thomax WMS | `WMS_CLUSTER`, `WMS_INSTANCE_CODE`, `WMS_TENANT_CODE`, `WMS_WAREHOUSE_CODE`, `WMS_API_KEY`, or Settings → WMS Integration | Dashboard |
| Apple push | `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_BUNDLE_ID`, `APNS_PRIVATE_KEY`, `APNS_SANDBOX` | DriverAPI (and Dashboard for its push sender) |
| External order API | `EXTERNAL_API_KEY` for authorized integrations | DriverAPI |

Do not use dummy secret values. Missing-provider pages remain visible with setup instructions. Manual addresses and local item-master management remain available without provider credentials. Email already uses Railway-managed Resend configuration.

The new database intentionally contains no historical orders or accounts. Delivery evidence is stored in the database. Browser sign-in does not provide background GPS or iOS push registration; those need the iOS app. The missing Swift source has not been recovered by this website update.

Validation: `python -m unittest discover -s tests -v` covers partner order isolation/approval/suspension, password-required driver login, lockout, session revocation, and assigned-order API authorization. Streamlit AppTest and browser checks cover navigation with empty and populated local databases.

## Workflow verification, 13 October 2026

The driver API now returns dispatch-created runs and preserves their stop order. Orders assigned directly are shown separately as unplanned deliveries. Run progress follows saved delivery outcomes; cancellation preserves delivered/failed orders and releases only unfinished assignments. Dashboard actions read fresh operational data on rerun. The browser driver portal also exposes profile, online/offline requests, run selection, closed stops, and refresh controls.

Local regression tests cover the dispatch-to-driver workflow, evidence persistence, run progress/completion, cancellation, profile, availability requests, location updates and two-way messages, plus the access-control tests. All 14 dashboard pages render with the populated test database. These checks do not verify external WMS, Google Places or APNs without their credentials, nor do they recover historical records or the native app.

## Starshipit

The administrator Starshipit page supports incoming order sync and queued supported writeback. Credentials and background syncing remain unset by default. See [Starshipit integration](STARSHIPIT_INTEGRATION.md) for configuration, tests and API limitations.
