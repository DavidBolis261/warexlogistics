from collections import OrderedDict

from api.client import DotWmsClient


def upsert_asn_receipt(client: DotWmsClient, receipt_data: dict):
    """Create or update an ASN receipt in .wms.

    Endpoint: /api/1.0/UpsertASNReceipt/
    """
    request = client._build_payload(OrderedDict())

    request['ShipmentNumber'] = receipt_data['shipment_number']

    if receipt_data.get('container_type'):
        request['ContainerType'] = receipt_data['container_type']
    if receipt_data.get('due_date'):
        request['DueDate'] = receipt_data['due_date']
    if receipt_data.get('receipt_reference'):
        request['ReceiptReference'] = receipt_data['receipt_reference']
    if receipt_data.get('supplier_name'):
        request['SupplierName'] = receipt_data['supplier_name']

    # Build lines
    lines = []
    for line_data in receipt_data.get('lines', []):
        line = OrderedDict()
        line['ItemCode'] = line_data['item_code']
        line['ExpectedQuantity'] = str(line_data['expected_quantity'])
        if line_data.get('trade_unit_level'):
            line['TradeUnitLevel'] = line_data['trade_unit_level']
        if line_data.get('expected_batch_number'):
            line['ExpectedBatchNumber'] = line_data['expected_batch_number']
        lines.append(line)

    if len(lines) == 1:
        request['Line'] = lines[0]
    else:
        request['Line'] = lines

    payload = OrderedDict([
        ('ASNReceipt', [request])
    ])

    return client.post('UpsertASNReceipt', payload)


def upsert_simple_receipt(client: DotWmsClient, receipt_data: dict):
    """Create a simple receipt in .wms.

    Endpoint: /api/1.0/UpsertSimpleReceipt/
    """
    request = client._build_payload(OrderedDict())

    request['ShipmentNumber'] = receipt_data['shipment_number']

    if receipt_data.get('due_date'):
        request['DueDate'] = receipt_data['due_date']
    if receipt_data.get('supplier_name'):
        request['SupplierName'] = receipt_data['supplier_name']

    lines = []
    for line_data in receipt_data.get('lines', []):
        line = OrderedDict()
        line['ItemCode'] = line_data['item_code']
        line['ExpectedQuantity'] = str(line_data['expected_quantity'])
        lines.append(line)

    if len(lines) == 1:
        request['Line'] = lines[0]
    else:
        request['Line'] = lines

    payload = OrderedDict([
        ('SimpleReceipt', [request])
    ])

    return client.post('UpsertSimpleReceipt', payload)


def cancel_receipt(client: DotWmsClient, shipment_number: str, reason: str = ''):
    """Cancel a receipt job in .wms.

    Endpoint: /api/1.0/CancelReceiptJob/
    Note: Can re-upload the same shipment number after cancellation.
    """
    request = client._build_payload(OrderedDict(), include_warehouse=False)
    request['ShipmentNumber'] = shipment_number
    if reason:
        request['CancelReason'] = reason

    payload = OrderedDict([
        ('CancelReceiptingJob', [request])
    ])

    return client.post('CancelReceiptJob', payload)
