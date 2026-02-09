import json
from collections import OrderedDict

import requests

from config.settings import WmsConfig


class DotWmsClient:
    """Core HTTP client for the Thomax .wms API.

    All .wms API operations are POST requests with JSON bodies.
    Auth credentials are embedded in the request body, not headers.
    JSON field order matters per the documentation.
    """

    def __init__(self, config: WmsConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _auth_fields(self, include_warehouse=True):
        """Return ordered auth fields to inject at the start of payloads."""
        fields = OrderedDict()
        fields['InstanceCode'] = self.config.instance_code
        fields['TenantCode'] = self.config.tenant_code
        if include_warehouse and self.config.warehouse_code:
            fields['WarehouseCode'] = self.config.warehouse_code
        fields['APIKey'] = self.config.api_key
        return fields

    def _build_payload(self, data: dict, include_warehouse=True):
        """Merge auth fields at the start of a payload dict, preserving order."""
        auth = self._auth_fields(include_warehouse)
        merged = OrderedDict(list(auth.items()) + list(data.items()))
        return merged

    def post(self, operation: str, payload, timeout=30):
        """Send a POST request to a .wms API endpoint.

        Args:
            operation: The API operation name (e.g., 'UpsertFulfilmentRequest')
            payload: The full request body (dict or OrderedDict)
            timeout: Request timeout in seconds

        Returns:
            dict with 'success', 'status_code', 'response', and optionally 'error'
        """
        url = f"{self.config.base_url}/{operation}/"

        try:
            # Use json.dumps with sort_keys=False to preserve insertion order
            body = json.dumps(payload, default=str)
            response = self.session.post(url, data=body, timeout=timeout)

            result = {
                'success': response.ok,
                'status_code': response.status_code,
                'response_text': response.text,
            }

            try:
                result['response'] = response.json()
            except (json.JSONDecodeError, ValueError):
                result['response'] = response.text

            if not response.ok:
                result['error'] = f"HTTP {response.status_code}: {response.text[:500]}"

            return result

        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f"Connection failed: Could not reach {url}. Check your cluster name.",
                'exception': str(e),
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f"Request timed out after {timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Request failed: {str(e)}",
            }

    def test_connection(self):
        """Test connectivity to the .wms API.

        Since there's no dedicated health endpoint, we verify
        the base URL is reachable.
        """
        try:
            url = f"{self.config.base_url}/"
            response = self.session.get(url, timeout=10)
            return {
                'success': True,
                'status_code': response.status_code,
                'message': f"Endpoint reachable (HTTP {response.status_code})",
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f"Cannot reach {self.config.base_url}. Check your cluster name.",
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Connection timed out",
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
            }
