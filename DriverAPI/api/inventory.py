from collections import OrderedDict

from api.client import DotWmsClient


def upsert_item_master_data(client: DotWmsClient, item_data: dict):
    """Create or update item master data in .wms.

    Endpoint: /api/1.0/UpsertItemMasterData/
    """
    request = client._build_payload(OrderedDict(), include_warehouse=False)

    request['ItemCode'] = item_data['item_code']
    request['ItemName'] = item_data.get('item_name', item_data['item_code'])

    if item_data.get('item_group'):
        request['ItemGroup'] = item_data['item_group']
    if item_data.get('barcode'):
        request['Barcode'] = item_data['barcode']
    if item_data.get('weight'):
        request['ItemWeight'] = str(item_data['weight'])
    if item_data.get('length'):
        request['ItemLength'] = str(item_data['length'])
    if item_data.get('width'):
        request['ItemWidth'] = str(item_data['width'])
    if item_data.get('height'):
        request['ItemHeight'] = str(item_data['height'])
    if item_data.get('unit_of_measure'):
        request['UnitOfMeasure'] = item_data['unit_of_measure']
    if item_data.get('inner_qty') and item_data['inner_qty'] > 0:
        request['InnerQuantity'] = str(item_data['inner_qty'])
    if item_data.get('outer_qty') and item_data['outer_qty'] > 0:
        request['OuterQuantity'] = str(item_data['outer_qty'])
    if item_data.get('pallet_qty') and item_data['pallet_qty'] > 0:
        request['PalletQuantity'] = str(item_data['pallet_qty'])

    payload = OrderedDict([
        ('ItemMasterData', request)
    ])

    return client.post('UpsertItemMasterData', payload)


def delete_item_master_data(client: DotWmsClient, item_code: str):
    """Delete item master data from .wms.

    Endpoint: /api/1.0/DeleteItemMasterData/
    Note: Only works if the item has no receipts, orders, or stock.
    """
    request = client._build_payload(OrderedDict(), include_warehouse=False)
    request['ItemCode'] = item_code

    payload = OrderedDict([
        ('DeleteItemMasterData', request)
    ])

    return client.post('DeleteItemMasterData', payload)


def upsert_item_warehouse_record(client: DotWmsClient, record_data: dict):
    """Create or update item warehouse record in .wms.

    Endpoint: /api/1.0/UpsertItemWarehouseRecord/
    """
    request = client._build_payload(OrderedDict())

    request['ItemCode'] = record_data['item_code']

    if record_data.get('standard_bin_location'):
        request['StandardBinLocation'] = record_data['standard_bin_location']
    if record_data.get('pick_face_min_stock') is not None:
        request['PickFaceMinStock'] = str(record_data['pick_face_min_stock'])
    if record_data.get('pick_face_max_stock') is not None:
        request['PickFaceMaxStock'] = str(record_data['pick_face_max_stock'])

    payload = OrderedDict([
        ('ItemWarehouseRecords', OrderedDict([
            ('ItemWarehouseRecord', request)
        ]))
    ])

    return client.post('UpsertItemWarehouseRecord', payload)
