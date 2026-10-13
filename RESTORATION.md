# Warex Railway restoration

Railway project: Warex Logistics. The Dashboard and DriverAPI share the Postgres service through `DATABASE_URL=${{Postgres.DATABASE_URL}}`.

Deployment settings are managed in Railway. Legacy conflicting railway.json/toml files have been removed.

| Service | Root | Start | Health | Port |
| --- | --- | --- | --- | --- |
| Dashboard | /WebPlatform | bash start.sh | /_stcore/health | 8501 |
| DriverAPI | /DriverAPI | gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 driver_api_server:app | /health | 5000 |

Both use Railpack and Python 3.12. Set SITE_DOMAIN=app.warexlogistics.com.au, TZ=Australia/Sydney, RESEND_API_KEY and EMAIL_FROM_ADDRESS on both services. Credentials belong only in Railway variables.

The first administrator must supply ADMIN_SETUP_TOKEN from the protected local handover file, then choose a username and password. The setup screen disappears once an administrator exists. Remove ADMIN_SETUP_TOKEN after setup. Never set RESET_ADMIN in production.

Partner registration and the client portal are unavailable during restoration because company data isolation needs repair. Driver login remains disabled until the iOS authentication flow is secured; ENABLE_DRIVER_LOGIN must remain false. The external API fails closed unless EXTERNAL_API_KEY is explicitly configured. Do not enable these entry points with live customer data without addressing those issues.

The new database intentionally contains no historical orders or accounts. Proof-of-delivery upload storage and APNs must be reviewed during iOS restoration before driver operations resume.
