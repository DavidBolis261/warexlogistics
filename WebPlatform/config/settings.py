import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass


class WmsConfig:
    """Resolves WMS credentials from session state, environment, or Streamlit secrets."""

    @property
    def cluster(self):
        return (
            st.session_state.get('wms_cluster')
            or os.getenv('WMS_CLUSTER')
            or self._from_secrets('cluster')
            or ''
        )

    @property
    def instance_code(self):
        return (
            st.session_state.get('wms_instance_code')
            or os.getenv('WMS_INSTANCE_CODE')
            or self._from_secrets('instance_code')
            or ''
        )

    @property
    def tenant_code(self):
        return (
            st.session_state.get('wms_tenant_code')
            or os.getenv('WMS_TENANT_CODE')
            or self._from_secrets('tenant_code')
            or ''
        )

    @property
    def warehouse_code(self):
        return (
            st.session_state.get('wms_warehouse_code')
            or os.getenv('WMS_WAREHOUSE_CODE')
            or self._from_secrets('warehouse_code')
            or ''
        )

    @property
    def api_key(self):
        return (
            st.session_state.get('wms_api_key')
            or os.getenv('WMS_API_KEY')
            or self._from_secrets('api_key')
            or ''
        )

    @property
    def base_url(self):
        if self.cluster:
            return f"https://{self.cluster}.dotwms.com/api/1.0"
        return ''

    @property
    def is_configured(self):
        return all([self.cluster, self.instance_code, self.tenant_code, self.api_key])

    def _from_secrets(self, key):
        try:
            return st.secrets.get('wms', {}).get(key)
        except Exception:
            return None

    def save_to_session(self, cluster, instance_code, tenant_code, warehouse_code, api_key):
        st.session_state['wms_cluster'] = cluster
        st.session_state['wms_instance_code'] = instance_code
        st.session_state['wms_tenant_code'] = tenant_code
        st.session_state['wms_warehouse_code'] = warehouse_code
        st.session_state['wms_api_key'] = api_key

    def save_to_env_file(self, cluster, instance_code, tenant_code, warehouse_code, api_key):
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        with open(env_path, 'w') as f:
            f.write(f"WMS_CLUSTER={cluster}\n")
            f.write(f"WMS_INSTANCE_CODE={instance_code}\n")
            f.write(f"WMS_TENANT_CODE={tenant_code}\n")
            f.write(f"WMS_WAREHOUSE_CODE={warehouse_code}\n")
            f.write(f"WMS_API_KEY={api_key}\n")


wms_config = WmsConfig()
