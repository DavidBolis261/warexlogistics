from collections import OrderedDict

from api.client import DotWmsClient


def adjust_uld_stock(client: DotWmsClient, adjustment_data: dict):
    """Adjust stock on a specific ULD in .wms.

    Endpoint: /api/1.0/AdjustULDStock/
    Note: Throws 'Adjustment from API' transaction type (distinct from manual adjustments).
    """
    request = client._build_payload(OrderedDict())

    request['ULDBarcode'] = adjustment_data['uld_barcode']
    request['ItemCode'] = adjustment_data['item_code']

    if adjustment_data.get('batch_number'):
        request['BatchNumber'] = adjustment_data['batch_number']
    if adjustment_data.get('serial_number'):
        request['SerialNumber'] = adjustment_data['serial_number']

    request['AdjustByQuantity'] = str(adjustment_data['quantity'])

    if adjustment_data.get('comment'):
        request['Comment'] = adjustment_data['comment']
    if adjustment_data.get('allow_negatives'):
        request['AllowNegatives'] = adjustment_data['allow_negatives']

    payload = OrderedDict([
        ('Adjustments', OrderedDict([
            ('Adjustment', request)
        ]))
    ])

    return client.post('AdjustULDStock', payload)


def create_uld(client: DotWmsClient, uld_data: dict):
    """Create a ULD in .wms.

    Endpoint: /api/1.0/CreateULD/
    Note: If barcode is omitted, next sequence number is used.
          If bin code is omitted, a null location is created.
    """
    request = client._build_payload(OrderedDict())

    if uld_data.get('barcode'):
        request['ULDBarcode'] = uld_data['barcode']
    if uld_data.get('held_reason'):
        request['ULDHeldReason'] = uld_data['held_reason']
    if uld_data.get('bin_code'):
        request['BinCode'] = uld_data['bin_code']

    # Add lines (initial stock)
    for line_data in uld_data.get('lines', []):
        line = OrderedDict()
        line['ItemCode'] = line_data['item_code']
        if line_data.get('batch_number'):
            line['BatchNumber'] = line_data['batch_number']
        line['Quantity'] = str(line_data['quantity'])
        request['Line'] = line

    payload = OrderedDict([
        ('CreateULDs', OrderedDict([
            ('CreateULD', request)
        ]))
    ])

    return client.post('CreateULD', payload)


def destroy_uld(client: DotWmsClient, uld_barcode: str):
    """Destroy/decommission a ULD in .wms.

    Endpoint: /api/1.0/DestroyULD/
    Note: If a ULD has already been destroyed, the response will say
          'ULD is on hold with a message of ULD Destroyed'.
    """
    request = client._build_payload(OrderedDict())
    request['ULDBarcode'] = uld_barcode

    payload = OrderedDict([
        ('Destructions', OrderedDict([
            ('Destruction', request)
        ]))
    ])

    return client.post('DestroyULD', payload)


def move_uld(client: DotWmsClient, uld_barcode: str, new_location: str):
    """Move a ULD to a new location in .wms.

    Endpoint: /api/1.0/MoveULD/
    """
    request = client._build_payload(OrderedDict())
    request['ULDBarcode'] = uld_barcode
    request['NewLocation'] = new_location

    payload = OrderedDict([
        ('Movements', OrderedDict([
            ('Movement', request)
        ]))
    ])

    return client.post('MoveULD', payload)
