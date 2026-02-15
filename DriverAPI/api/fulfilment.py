from collections import OrderedDict
from datetime import datetime

from api.client import DotWmsClient


def upsert_fulfilment_request(client: DotWmsClient, order_data: dict):
    """Create or update a fulfilment request in .wms.

    Endpoint: /api/1.0/UpsertFulfilmentRequest/
    """
    # Build the inner request with auth
    request = client._build_payload(OrderedDict())

    request['SalesOrderNumber'] = order_data['order_id']
    request['ParentCustomerCode'] = order_data.get('parent_customer_code', 'SMC')
    request['CustomerCode'] = order_data.get('customer_code', 'SMC')
    request['OrderDate'] = order_data.get('order_date', datetime.now().strftime('%Y-%m-%d'))

    priority_map = {'express': 3, 'standard': 2, 'economy': 1}
    request['JobPriority'] = str(priority_map.get(order_data.get('service_level', 'standard'), 2))

    if order_data.get('carrier_service'):
        request['CarrierServiceCode'] = order_data['carrier_service']

    request['DeliveryName'] = order_data['customer']
    if order_data.get('delivery_company'):
        request['DeliveryCompany'] = order_data['delivery_company']
    request['DeliveryAddress1'] = order_data['address']
    if order_data.get('address2'):
        request['DeliveryAddress2'] = order_data['address2']
    if order_data.get('suburb'):
        request['DeliverySuburb'] = order_data['suburb']
    if order_data.get('state'):
        request['DeliveryState'] = order_data['state']
    if order_data.get('postcode'):
        request['DeliveryPostcode'] = order_data['postcode']
    request['DeliveryCountry'] = order_data.get('country', 'Australia')
    if order_data.get('email'):
        request['DeliveryEmail'] = order_data['email']
    if order_data.get('phone'):
        request['DeliveryPhone'] = order_data['phone']

    if order_data.get('special_instructions'):
        request['FreightSpecialInstructions'] = order_data['special_instructions']

    # Build line item
    line = OrderedDict()
    line['WarehouseCode'] = client.config.warehouse_code
    line['ItemCode'] = order_data.get('item_code', 'PARCEL')
    line['Quantity'] = str(order_data.get('parcels', 1))
    request['Line'] = line

    # Wrap in the expected structure
    payload = OrderedDict([
        ('FulfilmentRequest', [request])
    ])

    return client.post('UpsertFulfilmentRequest', payload)


def cancel_sales_order(client: DotWmsClient, order_id: str):
    """Cancel a sales order / pack job in .wms.

    Endpoint: /api/1.0/CancelSalesOrder/
    Note: Once cancelled, it cannot be reopened.
    """
    request = client._build_payload(OrderedDict(), include_warehouse=False)
    request['PackSlipNumber'] = order_id

    payload = OrderedDict([
        ('CancelPackingSlip', [request])
    ])

    return client.post('CancelSalesOrder', payload)
