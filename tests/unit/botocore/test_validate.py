from tests import unittest
from datetime import datetime
import decimal

from botocore.compat import six
from botocore.model import ShapeResolver
from botocore.validate import ParamValidator

BOILER_PLATE_SHAPES = {
    'StringType': {
        'type': 'string'
    }
}


class BaseTestValidate(unittest.TestCase):

    def assert_has_validation_errors(self, given_shapes, input_params, errors):
        # Given the shape definitions ``given_shape`` and the user input
        # parameters ``input_params``, verify that the validation has
        # validation errors containing the list of ``errors``.
        # Also, this assumes the input shape name is "Input".
        errors_found = self.get_validation_error_message(
            given_shapes, input_params)
        self.assertTrue(errors_found.has_errors())
        error_message = errors_found.generate_report()
        for error in errors:
            self.assertIn(error, error_message)

    def get_validation_error_message(self, given_shapes, input_params):
        s = ShapeResolver(given_shapes)
        input_shape = s.get_shape_by_name('Input')
        validator = ParamValidator()
        errors_found = validator.validate(input_params, input_shape)
        error_message = errors_found.generate_report()
        return errors_found


class TestValidateRequiredParams(BaseTestValidate):
    def test_validate_required_params(self):
        self.assert_has_validation_errors(
            given_shapes={
                'Input': {
                    'type': 'structure',
                    'required': ['A', 'B'],
                    'members': {
                        'A': {'shape': 'StringType'},
                        'B': {'shape': 'StringType'}
                    }
                },
                'StringType': {'type': 'string'}
            },
            input_params={'A': 'foo'},
            errors=['Missing required parameter'])

    def test_validate_nested_required_param(self):
        self.assert_has_validation_errors(
            given_shapes={
                'Input': {
                    'type': 'structure',
                    'members': {
                        'A': {'shape': 'SubStruct'}
                    }
                },
                'SubStruct': {
                    'type': 'structure',
                    'required': ['B', 'C'],
                    'members': {
                        'B': {'shape': 'StringType'},
                        'C': {'shape': 'StringType'},
                    }
                },
                'StringType': {
                    'type': 'string',
                }
            },
            input_params={'A': {'B': 'foo'}},
            errors=['Missing required parameter'])

    def test_validate_unknown_param(self):
        self.assert_has_validation_errors(
            given_shapes={
                'Input': {
                    'type': 'structure',
                    'required': ['A'],
                    'members': {
                        'A': {'shape': 'StringType'},
                    }
                },
                'StringType': {'type': 'string'}
            },
            input_params={'A': 'foo', 'B': 'bar'},
            errors=['Unknown parameter'])


class TestValidateJSONValueTrait(BaseTestValidate):
    def test_accepts_jsonvalue_string(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'json': {
                        'shape': 'StrType',
                        'jsonvalue': True,
                        'location': 'header',
                        'locationName': 'header-name'
                    }
                }
            },
            'StrType': {'type': 'string'}
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'json': {'data': [1, 2.3, '3'], 'unicode': u'\u2713'}
            })
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_validate_jsonvalue_string(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'json': {
                        'shape': 'StrType',
                        'jsonvalue': True,
                        'location': 'header',
                        'locationName': 'header-name'
                    }
                }
            },
            'StrType': {'type': 'string'}
        }

        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'json': {'date': datetime(2017, 4, 27, 0, 0)}
            },
            errors=[
                ('Invalid parameter json must be json serializable: ')
            ])


class TestValidateDocumentType(BaseTestValidate):
    def test_accepts_document_type_string(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'inlineDocument': {
                        'shape': 'DocumentType',
                    }
                }
            },
            'DocumentType': {
                'type': 'structure',
                'document': True
            }
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'inlineDocument': {'data': [1, 2.3, '3',
                                            {'foo': None}],
                                   'unicode': u'\u2713'}
            })
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')


    def test_validate_document_type_string(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'inlineDocument': {
                        'shape': 'DocumentType',
                    }
                }
            },
            'DocumentType': {
                'type': 'structure',
                'document': True
            }
        }

        invalid_document = object()
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'inlineDocument': {
                    'number': complex(1j),
                    'date': datetime(2017, 4, 27, 0, 0),
                    'list': [invalid_document],
                    'dict': {'foo': (1, 2, 3)}
                }
            },
            errors=[
                ('Invalid type for document parameter number'),
                ('Invalid type for document parameter date'),
                ('Invalid type for document parameter list[0]'),
                ('Invalid type for document parameter foo'),
            ])


class TestValidateTaggedUnion(BaseTestValidate):
    def test_accepts_one_member(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'taggedUnion': {
                        'shape': 'TaggedUnionType',
                    }
                }
            },
            'TaggedUnionType': {
                'type': 'structure',
                'union': True,
                'members': {
                    'Foo': {'shape': 'StringType'},
                    'Bar': {'shape': 'StringType'},
                }
            },
            'StringType': {'type': 'string'}
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'taggedUnion': {'Foo': "mystring"}
            }
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')


    def test_validate_one_member_is_set(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'taggedUnion': {
                        'shape': 'TaggedUnionType',
                    }
                }
            },
            'TaggedUnionType': {
                'type': 'structure',
                'union': True,
                'members': {
                    'Foo': {'shape': 'StringType'},
                    'Bar': {'shape': 'StringType'},
                }
            },
            'StringType': {'type': 'string'}
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'taggedUnion': {'Foo': "mystring",
                                'Bar': "mystring2"
                                }
            }
        )
        error_msg = errors.generate_report()
        self.assertIn(
            'Invalid number of parameters set for tagged union structure',
            error_msg
        )

    def test_validate_known_member_is_set(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'taggedUnion': {
                        'shape': 'TaggedUnionType',
                    }
                }
            },
            'TaggedUnionType': {
                'type': 'structure',
                'union': True,
                'members': {
                    'Foo': {'shape': 'StringType'},
                    'Bar': {'shape': 'StringType'},
                }
            },
            'StringType': {'type': 'string'}
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'taggedUnion': {'unknown': "mystring"}
            }
        )
        error_msg = errors.generate_report()
        self.assertIn('Unknown parameter in taggedUnion', error_msg)

    def test_validate_structure_is_not_empty(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'taggedUnion': {
                        'shape': 'TaggedUnionType',
                    }
                }
            },
            'TaggedUnionType': {
                'type': 'structure',
                'union': True,
                'members': {
                    'Foo': {'shape': 'StringType'},
                    'Bar': {'shape': 'StringType'},
                }
            },
            'StringType': {'type': 'string'}
        }
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'taggedUnion': {}
            }
        )
        error_msg = errors.generate_report()
        self.assertIn('Must set one of the following keys', error_msg)


class TestValidateTypes(BaseTestValidate):
    def setUp(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'Str': {'shape': 'StrType'},
                    'Int': {'shape': 'IntType'},
                    'Bool': {'shape': 'BoolType'},
                    'List': {'shape': 'ListType'},
                    'Struct': {'shape': 'StructType'},
                    'Double': {'shape': 'DoubleType'},
                    'Long': {'shape': 'LongType'},
                    'Map': {'shape': 'MapType'},
                    'Timestamp': {'shape': 'TimeType'},
                }
            },
            'StrType': {'type': 'string'},
            'IntType': {'type': 'integer'},
            'BoolType': {'type': 'boolean'},
            'ListType': {'type': 'list'},
            'StructType': {'type': 'structure'},
            'DoubleType': {'type': 'double'},
            'LongType': {'type': 'long'},
            'MapType': {'type': 'map'},
            'TimeType': {'type': 'timestamp'},
        }

    def test_validate_string(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Str': 24,
                'Int': 'notInt',
                'Bool': 'notBool',
                'List': 'notList',
                'Struct': 'notDict',
                'Double': 'notDouble',
                'Long': 'notLong',
                'Map': 'notDict',
                'Timestamp': 'notTimestamp',
            },
            errors=[
                'Invalid type for parameter Str',
                'Invalid type for parameter Int',
                'Invalid type for parameter Bool',
                'Invalid type for parameter List',
                'Invalid type for parameter Struct',
                'Invalid type for parameter Double',
                'Invalid type for parameter Long',
                'Invalid type for parameter Map',
                'Invalid type for parameter Timestamp',
            ]
        )

    def test_datetime_type_accepts_datetime_obj(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Timestamp': datetime.now(),})
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_datetime_accepts_string_timestamp(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Timestamp': '2014-01-01 12:00:00'})
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_can_handle_none_datetimes(self):
        # This is specifically to test a workaround a bug in dateutil
        # where low level exceptions can propogate back up to
        # us.
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Timestamp': None})
        error_msg = errors.generate_report()
        self.assertIn('Invalid type for parameter Timestamp', error_msg)


class TestValidateRanges(BaseTestValidate):
    def setUp(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'Int': {'shape': 'IntType'},
                    'Long': {'shape': 'IntType'},
                    'String': {'shape': 'StringType'},
                    'List': {'shape': 'ListType'},
                    'OnlyMin': {'shape': 'MinStrOnly'},
                    'OnlyMax': {'shape': 'MaxStrOnly'},
                }
            },
            'IntType': {
                'type': 'integer',
                'min': 0,
                'max': 1000,
            },
            'LongType': {
                'type': 'long',
                'min': 0,
                'max': 1000,
            },
            'StringType': {
                'type': 'string',
                'min': 1,
                'max': 10,
            },
            'MinStrOnly': {
                'type': 'string',
                'min': 1
            },
            'MaxStrOnly': {
                'type': 'string',
                'max': 10
            },
            'ListType': {
                'type': 'list',
                'min': 1,
                'max': 5,
                'member': {
                    'shape': 'StringType'
                }
            },
        }

    def test_less_than_range(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Int': -10,
                'Long': -10,
            },
            errors=[
                'Invalid value for parameter Int',
                'Invalid value for parameter Long',
            ]
        )

    def test_does_not_validate_greater_than_range(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'Int': 100000000,
                'Long': 100000000,
            },
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_within_range(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Int': 10})
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_string_min_length_contraint(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'String': '',
            },
            errors=[
                'Invalid length for parameter String',
            ]
        )

    def test_does_not_validate_string_max_length_contraint(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'String': 'more than ten characters',
            },
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_list_min_length_constraint(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'List': [],
            },
            errors=[
                'Invalid length for parameter List',
            ]
        )

    def test_does_not_validate_list_max_length_constraint(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'List': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
            },
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_only_min_value_specified(self):
        # min anx max don't have to both be provided.
        # It's valid to just have min with no max, and
        # vice versa.
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'OnlyMin': '',
            },
            errors=[
                'Invalid length for parameter OnlyMin',
            ]
        )

    def test_does_not_validate_max_when_only_max_value_specified(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={
                'OnlyMax': 'more than ten characters',
            },
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')


class TestValidateMapType(BaseTestValidate):
    def setUp(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'Map': {'shape': 'MapType'},
                }
            },
            'MapType': {
                'type': 'map',
                'key': {'shape': 'StringType'},
                'value': {'shape': 'StringType'},
            },
            'StringType': {
                'type': 'string',
                'min': 2,
            },
        }

    def test_validate_keys_and_values(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Map': {'foo': '', 'a': 'foobar'}
            },
            errors=[
                'Invalid length for parameter Map',
            ]
        )


class TestValidationFloatType(BaseTestValidate):
    def setUp(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'Float': {'shape': 'FloatType'},
                }
            },
            'FloatType': {
                'type': 'float',
                'min': 2,
                'max': 5,
            },
        }

    def test_range_float(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Float': 1,
            },
            errors=[
                'Invalid value for parameter Float',
            ]
        )

    def test_decimal_allowed(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Float': decimal.Decimal('2.12345')})
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_decimal_still_validates_range(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Float': decimal.Decimal('1'),
            },
            errors=[
                'Invalid value for parameter Float',
            ]
        )


class TestValidateTypeBlob(BaseTestValidate):
    def setUp(self):
        self.shapes = {
            'Input': {
                'type': 'structure',
                'members': {
                    'Blob': {'shape': 'BlobType'},
                }
            },
            'BlobType': {
                'type': 'blob',
                'min': 2,
                'max': 5,
            },
        }

    def test_validates_bytes(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Blob': b'12345'}
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_validates_bytearray(self):
        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Blob': bytearray(b'12345')},
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_validates_file_like_object(self):
        value = six.BytesIO(b'foo')

        errors = self.get_validation_error_message(
            given_shapes=self.shapes,
            input_params={'Blob': value},
        )
        error_msg = errors.generate_report()
        self.assertEqual(error_msg, '')

    def test_validate_type(self):
        self.assert_has_validation_errors(
            given_shapes=self.shapes,
            input_params={
                'Blob': 24,
            },
            errors=[
                'Invalid type for parameter Blob',
            ]
        )
