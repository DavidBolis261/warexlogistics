from collections import OrderedDict

from api.client import DotWmsClient


def create_kitting_job(client: DotWmsClient, job_data: dict):
    """Create a kitting or dekitting job in .wms.

    Endpoint: /api/1.0/UploadKitJob/
    Note: Only works with stock type composite items.
    """
    request = client._build_payload(OrderedDict())

    if job_data.get('kitting_type'):
        request['KittingType'] = job_data['kitting_type']
    request['PackSlipNumber'] = job_data['pack_slip_number']
    if job_data.get('order_number'):
        request['OrderNumber'] = job_data['order_number']
    request['OrderDate'] = job_data['order_date']

    if job_data.get('job_priority'):
        request['JobPriority'] = str(job_data['job_priority'])
    if job_data.get('packer_message'):
        request['PackerMessage'] = job_data['packer_message']

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
        ('KittingJobs', OrderedDict([
            ('KittingJob', request)
        ]))
    ])

    return client.post('UploadKitJob', payload)


def upsert_logistic_unit(client: DotWmsClient, unit_data: dict):
    """Create or update a logistic unit (carton) for a pack job.

    Endpoint: /api/1.0/UpsertLogisticUnit/
    """
    request = client._build_payload(OrderedDict())

    request['PackSlipNumber'] = unit_data['pack_slip_number']
    request['LogisticUnitNumber'] = unit_data['logistic_unit_number']

    if unit_data.get('sscc_number'):
        request['SSCCNumber'] = unit_data['sscc_number']

    # Lines
    lines = []
    for line_data in unit_data.get('lines', []):
        line = OrderedDict()
        line['ItemCode'] = line_data['item_code']
        line['Quantity'] = str(line_data['quantity'])
        lines.append(line)

    if lines:
        if len(lines) == 1:
            request['Line'] = lines[0]
        else:
            request['Line'] = lines

    payload = OrderedDict([
        ('LogisticUnits', OrderedDict([
            ('LogisticUnit', request)
        ]))
    ])

    return client.post('UpsertLogisticUnit', payload)
