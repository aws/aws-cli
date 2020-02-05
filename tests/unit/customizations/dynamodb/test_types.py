# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from decimal import Decimal
from awscli.testutils import unittest

from botocore.compat import six

from awscli.customizations.dynamodb.types import (
    Binary, TypeSerializer, TypeDeserializer
)


class TestBinary(unittest.TestCase):
    def test_bytes_input(self):
        data = Binary(b'\x01')
        self.assertEqual(b'\x01', data)
        self.assertEqual(b'\x01', data.value)

    def test_non_ascii_bytes_input(self):
        # Binary data that is out of ASCII range
        data = Binary(b'\x88')
        self.assertEqual(b'\x88', data)
        self.assertEqual(b'\x88', data.value)

    def test_bytearray_input(self):
        data = Binary(bytearray([1]))
        self.assertEqual(b'\x01', data)
        self.assertEqual(b'\x01', data.value)

    def test_unicode_throws_error(self):
        with self.assertRaises(TypeError):
            Binary(u'\u00e9')

    def test_integer_throws_error(self):
        with self.assertRaises(TypeError):
            Binary(1)

    def test_not_equal(self):
        self.assertTrue(Binary(b'\x01') != b'\x02')

    def test_str(self):
        self.assertEqual(Binary(b'\x01').__str__(), b'\x01')

    def test_repr(self):
        self.assertIn('Binary', repr(Binary(b'1')))


class TestSerializer(unittest.TestCase):
    def setUp(self):
        self.serializer = TypeSerializer()

    def test_serialize_unsupported_type(self):
        with self.assertRaisesRegexp(TypeError, 'Unsupported type'):
            self.serializer.serialize(object())

    def test_serialize_null(self):
        self.assertEqual(self.serializer.serialize(None), {'NULL': True})

    def test_serialize_boolean(self):
        self.assertEqual(self.serializer.serialize(False), {'BOOL': False})

    def test_serialize_integer(self):
        self.assertEqual(self.serializer.serialize(1), {'N': '1'})

    def test_serialize_decimal(self):
        self.assertEqual(
            self.serializer.serialize(Decimal('1.25')), {'N': '1.25'})

    def test_serialize_float_error(self):
        with self.assertRaisesRegexp(
                TypeError,
                'Float types are not supported. Use Decimal types instead'):
            self.serializer.serialize(1.25)

    def test_serialize_NaN_error(self):
        with self.assertRaisesRegexp(
                TypeError,
                'Infinity and NaN not supported'):
            self.serializer.serialize(Decimal('NaN'))

    def test_serialize_string(self):
        self.assertEqual(self.serializer.serialize('foo'), {'S': 'foo'})

    def test_serialize_binary(self):
        self.assertEqual(self.serializer.serialize(
            Binary(b'\x01')), {'B': b'\x01'})

    def test_serialize_bytearray(self):
        self.assertEqual(self.serializer.serialize(bytearray([1])),
                         {'B': b'\x01'})

    def test_serialize_bytes(self):
        self.assertEqual(self.serializer.serialize(b'\x01'), {'B': b'\x01'})

    def test_serialize_number_set(self):
        serialized_value = self.serializer.serialize(set([1, 2, 3]))
        self.assertEqual(len(serialized_value), 1)
        self.assertIn('NS', serialized_value)
        self.assertCountEqual(serialized_value['NS'], ['1', '2', '3'])

    def test_serialize_string_set(self):
        serialized_value = self.serializer.serialize(set(['foo', 'bar']))
        self.assertEqual(len(serialized_value), 1)
        self.assertIn('SS', serialized_value)
        self.assertCountEqual(serialized_value['SS'], ['foo', 'bar'])

    def test_serialize_binary_set(self):
        serialized_value = self.serializer.serialize(
            set([Binary(b'\x01'), Binary(b'\x02')]))
        self.assertEqual(len(serialized_value), 1)
        self.assertIn('BS', serialized_value)
        self.assertCountEqual(serialized_value['BS'], [b'\x01', b'\x02'])

    def test_serialize_list(self):
        serialized_value = self.serializer.serialize(['foo', 1, [1]])
        self.assertEqual(len(serialized_value), 1)
        self.assertIn('L', serialized_value)
        self.assertCountEqual(
            serialized_value['L'],
            [{'S': 'foo'}, {'N': '1'}, {'L': [{'N': '1'}]}]
        )

    def test_serialize_map(self):
        serialized_value = self.serializer.serialize(
            {'foo': 'bar', 'baz': {'biz': 1}})
        self.assertEqual(
            serialized_value,
            {'M': {'foo': {'S': 'bar'}, 'baz': {'M': {'biz': {'N': '1'}}}}})


class TestDeserializer(unittest.TestCase):
    def setUp(self):
        self.deserializer = TypeDeserializer()

    def test_deserialize_invalid_type(self):
        with self.assertRaisesRegexp(TypeError, 'FOO is not supported'):
            self.deserializer.deserialize({'FOO': 'bar'})

    def test_deserialize_empty_structure(self):
        with self.assertRaisesRegexp(TypeError, 'Value must be a nonempty'):
            self.assertEqual(self.deserializer.deserialize({}), {})

    def test_deserialize_null(self):
        self.assertEqual(self.deserializer.deserialize({"NULL": True}), None)

    def test_deserialize_boolean(self):
        self.assertEqual(self.deserializer.deserialize({"BOOL": False}), False)

    def test_deserialize_integer(self):
        self.assertEqual(
            self.deserializer.deserialize({'N': '1'}), Decimal('1'))

    def test_deserialize_decimal(self):
        self.assertEqual(
            self.deserializer.deserialize({'N': '1.25'}), Decimal('1.25'))

    def test_deserialize_string(self):
        self.assertEqual(
            self.deserializer.deserialize({'S': 'foo'}), 'foo')

    def test_deserialize_binary(self):
        self.assertEqual(
            self.deserializer.deserialize({'B': b'\x00'}), Binary(b'\x00'))

    def test_deserialize_number_set(self):
        self.assertEqual(
            self.deserializer.deserialize(
                {'NS': ['1', '1.25']}), set([Decimal('1'), Decimal('1.25')]))

    def test_deserialize_string_set(self):
        self.assertEqual(
            self.deserializer.deserialize(
                {'SS': ['foo', 'bar']}), set(['foo', 'bar']))

    def test_deserialize_binary_set(self):
        self.assertEqual(
            self.deserializer.deserialize(
                {'BS': [b'\x00', b'\x01']}),
            set([Binary(b'\x00'), Binary(b'\x01')]))

    def test_deserialize_list(self):
        self.assertEqual(
            self.deserializer.deserialize(
                {'L': [{'N': '1'}, {'S': 'foo'}, {'L': [{'N': '1.25'}]}]}),
            [Decimal('1'), 'foo', [Decimal('1.25')]])

    def test_deserialize_map(self):
        self.assertEqual(
            self.deserializer.deserialize(
                {'M': {'foo': {'S': 'mystring'},
                       'bar': {'M': {'baz': {'N': '1'}}}}}),
            {'foo': 'mystring', 'bar': {'baz': Decimal('1')}}
        )
