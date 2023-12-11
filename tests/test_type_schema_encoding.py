from pprint import pprint
from unittest import TestCase

from pypg import Property, decode, encode, get_fully_qualified_name
from pypg.traits import Observable, Unit
from tests.test_property import Example


class ComplexExample(Example):
    ex = Property[Example]()
    ex2 = Property[Example]()


class TypeSchemaEncodingTest(TestCase):
    def test_property_type_encoding(self):
        enc = encode(ComplexExample)
        pprint(enc)
        fqn, (data, type_id) = enc
        self.assertEqual(fqn, get_fully_qualified_name(ComplexExample))
        a_fqn, (a_data, a_id) = data['a']
        self.assertEqual(a_fqn, get_fully_qualified_name(type(ComplexExample.a)))
        self.assertEqual(a_data['value_type'], encode(float))
        self.assertEqual(a_data['traits'], [])
        d_fqn, (d_data, d_id) = data['d']
        d_traits = d_data['traits']
        d_trait_types = {trait_type: data for trait_type, data in d_traits}
        self.assertIn(get_fully_qualified_name(Observable), d_trait_types)
        d_unit, d_unit_id = d_trait_types[get_fully_qualified_name(Unit)]
        d_unit_data = d_unit['value']
        self.assertEqual(['str',"mm"], d_unit_data)

    def test_type_transcoding(self):
        enc = encode(int)
        self.assertEqual(['type', 'int'], enc)
        self.assertIs(int, decode(enc))

    def test_generic_encoding(self):
        schema = encode(tuple[float, float])
        self.assertEqual(schema, ['type', 'tuple[float,float]'])
