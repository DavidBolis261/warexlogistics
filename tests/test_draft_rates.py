import sys
from pathlib import Path
from decimal import Decimal
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from integrations.draft_rates import calculate_draft_base_freight,calculate_rate,CoveragePolicy


def request(parcels=None):
    place={'suburb':'Fixture Locality','postcode':'0000','state':'NSW','country':'AU'}
    return {'origin':dict(place),'destination':dict(place),
            'parcels':parcels if parcels is not None else [{'actual_weight_kg':'1'}]}


POLICY=CoveragePolicy('TEST-FIXTURE-NOT-SYDNEY',frozenset({('Fixture Locality','0000')}))


class RateTests(unittest.TestCase):
    def test_continuous_edges_and_ceil_after_five(self):
        cases={'0.000001':'5.70','1':'5.70','1.005':'6.70','3':'6.70','3.005':'7.70',
               '5':'7.70','5.000001':'8.10','6':'8.10','6.000001':'8.50','22':'14.50'}
        for weight,price in cases.items():
            with self.subTest(weight=weight):
                self.assertEqual(calculate_draft_base_freight(weight).base_freight_aud,Decimal(price))

    def test_invalid_weights(self):
        for value in ('0','-1','22.00001','NaN','Infinity','sNaN',True,1.1,None,{},'1e-999999'):
            with self.subTest(value=value),self.assertRaises(ValueError):calculate_draft_base_freight(value)

    def test_multi_parcel_sum_and_cap_is_per_parcel(self):
        result=calculate_rate(request([{'actual_weight_kg':'22'},{'actual_weight_kg':'22'}]),POLICY)
        self.assertTrue(result['quote_ready']);self.assertEqual(result['total_aud'],'29.00')
        self.assertEqual(result['fuel_in_quote_aud'],'0.00');self.assertTrue(result['base_freight_gst_included'])
        with self.assertRaises(ValueError):calculate_rate(request([{'actual_weight_kg':'23'}]),POLICY)

    def test_cover_excluded_unless_selected(self):
        result=calculate_rate(request([{'actual_weight_kg':'1','declared_value_aud':'1000'}]),POLICY)
        self.assertEqual(result['total_aud'],'5.70')
        self.assertEqual(result['cover_charge_aud'],'0.00')

    def test_selected_cover_is_gst_inclusive_and_in_total(self):
        for value,premium in [('5000','50.00'),('123.45','1.23'),('100.50','1.01')]:
            with self.subTest(value=value):
                result=calculate_rate(request([{'actual_weight_kg':'1','cover_selected':True,'declared_value_aud':value}]),POLICY)
                self.assertEqual(result['cover_charge_aud'],premium)
                self.assertTrue(result['quote_ready'])
                self.assertTrue(result['cover_gst_included'])
                self.assertEqual(Decimal(result['total_aud']),Decimal('5.70')+Decimal(premium))
                self.assertEqual(result['unresolved_rules'],[])
                self.assertEqual(result['parcels'][0]['cover_charge_aud'],premium)

    def test_cover_rounds_per_parcel_before_summing(self):
        result=calculate_rate(request([
            {'actual_weight_kg':'1','cover_selected':True,'declared_value_aud':'100.50'},
            {'actual_weight_kg':'1','cover_selected':True,'declared_value_aud':'100.50'},
            {'actual_weight_kg':'1','cover_selected':False,'declared_value_aud':'5000'},
        ]),POLICY)
        self.assertEqual(result['cover_charge_aud'],'2.02')
        self.assertEqual(result['base_freight_aud'],'17.10')
        self.assertEqual(result['total_aud'],'19.12')
        self.assertEqual(result['fuel_in_quote_aud'],'0.00')

    def test_invalid_cover_values_and_flags(self):
        for extra in ({'cover_selected':True},{'cover_selected':'yes'}, {'declared_value_aud':'5000.01'},
                      {'declared_value_aud':'0'},{'declared_value_aud':'0.001'},{'declared_value_aud':'NaN'}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                calculate_rate(request([dict(actual_weight_kg='1',**extra)]),POLICY)

    def test_no_default_geographic_coverage(self):
        result=calculate_rate(request())
        self.assertEqual(result['unresolved_rules'],['sydney_boundary_not_configured'])
        self.assertNotIn('total_aud',result)
        for field,value in [('suburb','Outside'),('postcode','9999'),('state','VIC'),('country','NZ')]:
            for end in ('origin','destination'):
                body=request();body[end][field]=value
                result=calculate_rate(body,POLICY)
                self.assertFalse(result['quote_ready']);self.assertNotIn('total_aud',result)

    def test_exact_location_pair_normalisation(self):
        body=request();body['origin']['suburb']='  fixture   locality ';body['destination']['state']='nsw'
        self.assertTrue(calculate_rate(body,POLICY)['quote_ready'])

    def test_bad_contract_input(self):
        cases=[{},[],request([]),request([{'actual_weight_kg':'1','cubic_weight_kg':'2'}])]
        body=request();body['origin']['postcode']='００００';cases.append(body)
        for body in cases:
            with self.assertRaises(ValueError):calculate_rate(body,POLICY)


if __name__=='__main__':unittest.main()
