from collections import OrderedDict
from datetime import datetime

from api.client import DotWmsClient


def upsert_pack_job(client: DotWmsClient, job_data: dict):
    """Create or update a pack job in .wms.

    Endpoint: /api/1.0/UpsertPackJob/
    """
    request = client._build_payload(OrderedDict())

    request['PackSlipNumber'] = job_data['pack_slip_number']
    request['SalesOrderNumber'] = job_data.get('sales_order_number', job_data['pack_slip_number'])
    request['ParentCustomerCode'] = job_data.get('parent_customer_code', 'SMC')
    request['CustomerCode'] = job_data.get('customer_code', 'SMC')
    request['OrderDate'] = job_data.get('order_date', datetime.now().strftime('%Y-%m-%d'))

    if job_data.get('pick_method'):
        request['PickMethod'] = job_data['pick_method']
    if job_data.get('pack_method'):
        request['PackMethod'] = job_data['pack_method']

    request['DeliveryName'] = job_data['delivery_name']
    request['DeliveryAddress1'] = job_data['delivery_address1']
    if job_data.get('delivery_suburb'):
        request['DeliverySuburb'] = job_data['delivery_suburb']
    if job_data.get('delivery_state'):
        request['DeliveryState'] = job_data['delivery_state']
    if job_data.get('delivery_postcode'):
        request['DeliveryPostcode'] = job_data['delivery_postcode']
    request['DeliveryCountry'] = job_data.get('delivery_country', 'Australia')

    # Lines
    lines = []
    for line_data in job_data.get('lines', []):
        line = OrderedDict()
        line['ItemCode'] = line_data['item_code']
        line['Quantity'] = str(line_data['quantity'])
        lines.append(line)

    if len(lines) == 1:
        request['Line'] = lines[0]
    else:
        request['Line'] = lines

    payload = OrderedDict([
        ('PackingSlips', OrderedDict([
            ('PackingSlip', request)
        ]))
    ])

    return client.post('UpsertPackJob', payload)


def cancel_pack_job(client: DotWmsClient, pack_slip_number: str):
    """Cancel a pack job in .wms.

    Endpoint: /api/1.0/CancelPackJob/
    Note: Once cancelled, it cannot be reopened.
    """
    request = client._build_payload(OrderedDict(), include_warehouse=False)
    request['PackSlipNumber'] = pack_slip_number

    payload = OrderedDict([
        ('CancelPackingSlip', [request])
    ])

    return client.post('CancelPackJob', payload)
