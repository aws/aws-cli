# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import io

import pytest

from tests import create_session
from tests import unittest
from tests import RawResponse
from tests import FreezeTime
from dateutil.tz import tzutc, tzoffset
import datetime
import copy
import mock
import operator

import botocore
from botocore import xform_name
from botocore.compat import OrderedDict, json
from botocore.compat import six
from botocore.awsrequest import AWSRequest, HeadersDict
from botocore.awsrequest import AWSResponse
from botocore.exceptions import InvalidExpressionError, ConfigNotFound
from botocore.exceptions import ClientError, ConnectionClosedError
from botocore.exceptions import InvalidDNSNameError, MetadataRetrievalError
from botocore.exceptions import PendingAuthorizationExpiredError
from botocore.model import ServiceModel
from botocore.session import Session
from botocore.exceptions import InvalidIMDSEndpointError
from botocore.exceptions import InvalidIMDSEndpointModeError
from botocore.exceptions import ReadTimeoutError
from botocore.exceptions import ConnectTimeoutError
from botocore.exceptions import UnsupportedS3ArnError
from botocore.exceptions import UnsupportedS3AccesspointConfigurationError
from botocore.exceptions import UnsupportedOutpostResourceError
from botocore.model import ServiceModel
from botocore.model import OperationModel
from botocore.regions import EndpointResolver
from botocore.utils import ensure_boolean
from botocore.utils import resolve_imds_endpoint_mode
from botocore.utils import is_json_value_header
from botocore.utils import remove_dot_segments
from botocore.utils import normalize_url_path
from botocore.utils import validate_jmespath_for_set
from botocore.utils import set_value_from_jmespath
from botocore.utils import parse_key_val_file_contents
from botocore.utils import parse_key_val_file
from botocore.utils import parse_timestamp
from botocore.utils import parse_to_aware_datetime
from botocore.utils import datetime2timestamp
from botocore.utils import CachedProperty
from botocore.utils import ArgumentGenerator
from botocore.utils import calculate_tree_hash
from botocore.utils import calculate_sha256
from botocore.utils import is_valid_endpoint_url
from botocore.utils import fix_s3_host
from botocore.utils import switch_to_virtual_host_style
from botocore.utils import instance_cache
from botocore.utils import merge_dicts
from botocore.utils import lowercase_dict
from botocore.utils import get_service_module_name
from botocore.utils import percent_encode_sequence
from botocore.utils import percent_encode
from botocore.utils import switch_host_s3_accelerate
from botocore.utils import deep_merge
from botocore.utils import S3RegionRedirector
from botocore.utils import InvalidArnException
from botocore.utils import ArnParser
from botocore.utils import S3ArnParamHandler
from botocore.utils import S3EndpointSetter
from botocore.utils import ContainerMetadataFetcher
from botocore.utils import InstanceMetadataFetcher
from botocore.utils import SSOTokenFetcher
from botocore.utils import SSOTokenLoader
from botocore.utils import is_valid_uri, is_valid_ipv6_endpoint_url
from botocore.utils import original_ld_library_path
from botocore.utils import has_header
from botocore.utils import determine_content_length
from botocore.exceptions import SSOTokenLoadError
from botocore.utils import IMDSFetcher
from botocore.utils import BadIMDSRequestError
from botocore.model import DenormalizedStructureBuilder
from botocore.model import ShapeResolver
from botocore.stub import Stubber
from botocore.config import Config

DATE = datetime.datetime(2021, 12, 10, 00, 00, 00)
DT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TestEnsureBoolean(unittest.TestCase):
    def test_boolean_true(self):
        self.assertEqual(ensure_boolean(True), True)

    def test_boolean_false(self):
        self.assertEqual(ensure_boolean(False), False)

    def test_string_true(self):
        self.assertEqual(ensure_boolean('True'), True)

    def test_string_false(self):
        self.assertEqual(ensure_boolean('False'), False)

    def test_string_lowercase_true(self):
        self.assertEqual(ensure_boolean('true'), True)

    def test_invalid_type_false(self):
        self.assertEqual(ensure_boolean({'foo': 'bar'}), False)


class TestResolveIMDSEndpointMode(unittest.TestCase):
    def create_session_with_config(self, endpoint_mode, imds_use_IPv6):
        session = create_session()
        session.set_config_variable('ec2_metadata_service_endpoint_mode',
                                    endpoint_mode)
        session.set_config_variable('imds_use_ipv6',
                                    imds_use_IPv6)
        return session

    def test_resolve_endpoint_mode_no_config(self):
        session = self.create_session_with_config(None, None)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv4')

    def test_resolve_endpoint_mode_IPv6(self):
        session = self.create_session_with_config('IPv6', None)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv6')

    def test_resolve_endpoint_mode_IPv6(self):
        session = self.create_session_with_config('IPv4', None)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv4')

    def test_resolve_endpoint_mode_none_use_IPv6_true(self):
        session = self.create_session_with_config(None, True)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv6')

    def test_resolve_endpoint_mode_none_use_IPv6_false(self):
        session = self.create_session_with_config(None, False)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv4')

    def test_resolve_endpoint_mode_IPv6_use_IPv6_false(self):
        session = self.create_session_with_config('IPv6', False)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv6')

    def test_resolve_endpoint_mode_IPv4_use_IPv6_true(self):
        session = self.create_session_with_config('IPv4', True)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv4')

    def test_resolve_endpoint_mode_IPv6_use_IPv6_true(self):
        session = self.create_session_with_config('IPv6', True)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv6')

    def test_resolve_endpoint_mode_IPv6_mixed_casing_use_IPv6_true(self):
        session = self.create_session_with_config('iPv6', None)
        self.assertEqual(resolve_imds_endpoint_mode(session), 'ipv6')

    def test_resolve_endpoint_mode_invalid_input(self):
        session = self.create_session_with_config('IPv3', True)
        with self.assertRaises(InvalidIMDSEndpointModeError):
            resolve_imds_endpoint_mode(session)


class TestIsJSONValueHeader(unittest.TestCase):
    def test_no_serialization_section(self):
        shape = mock.Mock()
        shape.type_name = 'string'
        self.assertFalse(is_json_value_header(shape))

    def test_non_jsonvalue_shape(self):
        shape = mock.Mock()
        shape.serialization = {
            'location': 'header'
        }
        shape.type_name = 'string'
        self.assertFalse(is_json_value_header(shape))

    def test_non_header_jsonvalue_shape(self):
        shape = mock.Mock()
        shape.serialization = {
            'jsonvalue': True
        }
        shape.type_name = 'string'
        self.assertFalse(is_json_value_header(shape))

    def test_non_string_jsonvalue_shape(self):
        shape = mock.Mock()
        shape.serialization = {
            'location': 'header',
            'jsonvalue': True
        }
        shape.type_name = 'integer'
        self.assertFalse(is_json_value_header(shape))

    def test_json_value_header(self):
        shape = mock.Mock()
        shape.serialization = {
            'jsonvalue': True,
            'location': 'header'
        }
        shape.type_name = 'string'
        self.assertTrue(is_json_value_header(shape))



class TestURINormalization(unittest.TestCase):
    def test_remove_dot_segments(self):
        self.assertEqual(remove_dot_segments('../foo'), 'foo')
        self.assertEqual(remove_dot_segments('../../foo'), 'foo')
        self.assertEqual(remove_dot_segments('./foo'), 'foo')
        self.assertEqual(remove_dot_segments('/./'), '/')
        self.assertEqual(remove_dot_segments('/../'), '/')
        self.assertEqual(remove_dot_segments('/foo/bar/baz/../qux'),
                         '/foo/bar/qux')
        self.assertEqual(remove_dot_segments('/foo/..'), '/')
        self.assertEqual(remove_dot_segments('foo/bar/baz'), 'foo/bar/baz')
        self.assertEqual(remove_dot_segments('..'), '')
        self.assertEqual(remove_dot_segments('.'), '')
        self.assertEqual(remove_dot_segments('/.'), '/')
        self.assertEqual(remove_dot_segments('/.foo'), '/.foo')
        self.assertEqual(remove_dot_segments('/..foo'), '/..foo')
        self.assertEqual(remove_dot_segments(''), '')
        self.assertEqual(remove_dot_segments('/a/b/c/./../../g'), '/a/g')
        self.assertEqual(remove_dot_segments('mid/content=5/../6'), 'mid/6')
        # I don't think this is RFC compliant...
        self.assertEqual(remove_dot_segments('//foo//'), '/foo/')

    def test_empty_url_normalization(self):
        self.assertEqual(normalize_url_path(''), '/')


class TestTransformName(unittest.TestCase):
    def test_upper_camel_case(self):
        self.assertEqual(xform_name('UpperCamelCase'), 'upper_camel_case')
        self.assertEqual(xform_name('UpperCamelCase', '-'), 'upper-camel-case')

    def test_lower_camel_case(self):
        self.assertEqual(xform_name('lowerCamelCase'), 'lower_camel_case')
        self.assertEqual(xform_name('lowerCamelCase', '-'), 'lower-camel-case')

    def test_consecutive_upper_case(self):
        self.assertEqual(xform_name('HTTPHeaders'), 'http_headers')
        self.assertEqual(xform_name('HTTPHeaders', '-'), 'http-headers')

    def test_consecutive_upper_case_middle_string(self):
        self.assertEqual(xform_name('MainHTTPHeaders'), 'main_http_headers')
        self.assertEqual(xform_name('MainHTTPHeaders', '-'),
                         'main-http-headers')

    def test_s3_prefix(self):
        self.assertEqual(xform_name('S3BucketName'), 's3_bucket_name')

    def test_already_snake_cased(self):
        self.assertEqual(xform_name('leave_alone'), 'leave_alone')
        self.assertEqual(xform_name('s3_bucket_name'), 's3_bucket_name')
        self.assertEqual(xform_name('bucket_s3_name'), 'bucket_s3_name')

    def test_special_cases(self):
        # Some patterns don't actually match the rules we expect.
        self.assertEqual(xform_name('SwapEnvironmentCNAMEs'),
                         'swap_environment_cnames')
        self.assertEqual(xform_name('SwapEnvironmentCNAMEs', '-'),
                         'swap-environment-cnames')
        self.assertEqual(xform_name('CreateCachediSCSIVolume', '-'),
                         'create-cached-iscsi-volume')
        self.assertEqual(xform_name('DescribeCachediSCSIVolumes', '-'),
                         'describe-cached-iscsi-volumes')
        self.assertEqual(xform_name('DescribeStorediSCSIVolumes', '-'),
                         'describe-stored-iscsi-volumes')
        self.assertEqual(xform_name('CreateStorediSCSIVolume', '-'),
                         'create-stored-iscsi-volume')
        self.assertEqual(xform_name('sourceServerIDs', '-'),
                         'source-server-ids')

    def test_special_case_ends_with_s(self):
        self.assertEqual(xform_name('GatewayARNs', '-'), 'gateway-arns')

    def test_partial_rename(self):
        transformed = xform_name('IPV6', '-')
        self.assertEqual(transformed, 'ipv6')
        transformed = xform_name('IPV6', '_')
        self.assertEqual(transformed, 'ipv6')

    def test_s3_partial_rename(self):
        transformed = xform_name('s3Resources', '-')
        self.assertEqual(transformed, 's3-resources')
        transformed = xform_name('s3Resources', '_')
        self.assertEqual(transformed, 's3_resources')


class TestValidateJMESPathForSet(unittest.TestCase):
    def setUp(self):
        super(TestValidateJMESPathForSet, self).setUp()
        self.data = {
            'Response': {
                'Thing': {
                    'Id': 1,
                    'Name': 'Thing #1',
                }
            },
            'Marker': 'some-token'
        }

    def test_invalid_exp(self):
        with self.assertRaises(InvalidExpressionError):
            validate_jmespath_for_set('Response.*.Name')

        with self.assertRaises(InvalidExpressionError):
            validate_jmespath_for_set('Response.Things[0]')

        with self.assertRaises(InvalidExpressionError):
            validate_jmespath_for_set('')

        with self.assertRaises(InvalidExpressionError):
            validate_jmespath_for_set('.')


class TestSetValueFromJMESPath(unittest.TestCase):
    def setUp(self):
        super(TestSetValueFromJMESPath, self).setUp()
        self.data = {
            'Response': {
                'Thing': {
                    'Id': 1,
                    'Name': 'Thing #1',
                }
            },
            'Marker': 'some-token'
        }

    def test_single_depth_existing(self):
        set_value_from_jmespath(self.data, 'Marker', 'new-token')
        self.assertEqual(self.data['Marker'], 'new-token')

    def test_single_depth_new(self):
        self.assertFalse('Limit' in self.data)
        set_value_from_jmespath(self.data, 'Limit', 100)
        self.assertEqual(self.data['Limit'], 100)

    def test_multiple_depth_existing(self):
        set_value_from_jmespath(self.data, 'Response.Thing.Name', 'New Name')
        self.assertEqual(self.data['Response']['Thing']['Name'], 'New Name')

    def test_multiple_depth_new(self):
        self.assertFalse('Brand' in self.data)
        set_value_from_jmespath(self.data, 'Brand.New', {'abc': 123})
        self.assertEqual(self.data['Brand']['New']['abc'], 123)


class TestParseEC2CredentialsFile(unittest.TestCase):
    def test_parse_ec2_content(self):
        contents = "AWSAccessKeyId=a\nAWSSecretKey=b\n"
        self.assertEqual(parse_key_val_file_contents(contents),
                         {'AWSAccessKeyId': 'a',
                          'AWSSecretKey': 'b'})

    def test_parse_ec2_content_empty(self):
        contents = ""
        self.assertEqual(parse_key_val_file_contents(contents), {})

    def test_key_val_pair_with_blank_lines(self):
        # The \n\n has an extra blank between the access/secret keys.
        contents = "AWSAccessKeyId=a\n\nAWSSecretKey=b\n"
        self.assertEqual(parse_key_val_file_contents(contents),
                         {'AWSAccessKeyId': 'a',
                          'AWSSecretKey': 'b'})

    def test_key_val_parser_lenient(self):
        # Ignore any line that does not have a '=' char in it.
        contents = "AWSAccessKeyId=a\nNOTKEYVALLINE\nAWSSecretKey=b\n"
        self.assertEqual(parse_key_val_file_contents(contents),
                         {'AWSAccessKeyId': 'a',
                          'AWSSecretKey': 'b'})

    def test_multiple_equals_on_line(self):
        contents = "AWSAccessKeyId=a\nAWSSecretKey=secret_key_with_equals=b\n"
        self.assertEqual(parse_key_val_file_contents(contents),
                         {'AWSAccessKeyId': 'a',
                          'AWSSecretKey': 'secret_key_with_equals=b'})

    def test_os_error_raises_config_not_found(self):
        mock_open = mock.Mock()
        mock_open.side_effect = OSError()
        with self.assertRaises(ConfigNotFound):
            parse_key_val_file('badfile', _open=mock_open)


class TestParseTimestamps(unittest.TestCase):
    def test_parse_iso8601(self):
        self.assertEqual(
            parse_timestamp('1970-01-01T00:10:00.000Z'),
            datetime.datetime(1970, 1, 1, 0, 10, tzinfo=tzutc()))

    def test_parse_epoch(self):
        self.assertEqual(
            parse_timestamp(1222172800),
            datetime.datetime(2008, 9, 23, 12, 26, 40, tzinfo=tzutc()))

    def test_parse_epoch_zero_time(self):
        self.assertEqual(
            parse_timestamp(0),
            datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc()))

    def test_parse_epoch_as_string(self):
        self.assertEqual(
            parse_timestamp('1222172800'),
            datetime.datetime(2008, 9, 23, 12, 26, 40, tzinfo=tzutc()))

    def test_parse_rfc822(self):
        self.assertEqual(
            parse_timestamp('Wed, 02 Oct 2002 13:00:00 GMT'),
            datetime.datetime(2002, 10, 2, 13, 0, tzinfo=tzutc()))

    def test_parse_gmt_in_uk_time(self):
        # In the UK the time switches from GMT to BST and back as part of
        # their daylight savings time. time.tzname will therefore report
        # both time zones. dateutil sees that the time zone is a local time
        # zone and so parses it as local time, but it ends up being BST
        # instead of GMT. To remedy this issue we can provide a time zone
        # context which will enforce GMT == UTC.
        with mock.patch('time.tzname', ('GMT', 'BST')):
            self.assertEqual(
                parse_timestamp('Wed, 02 Oct 2002 13:00:00 GMT'),
                datetime.datetime(2002, 10, 2, 13, 0, tzinfo=tzutc()))

    def test_parse_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            parse_timestamp('invalid date')

    def test_parse_timestamp_fails_with_bad_tzinfo(self):
        mock_tzinfo = mock.Mock()
        mock_tzinfo.__name__ = 'tzinfo'
        mock_tzinfo.side_effect = OSError()
        mock_get_tzinfo_options = mock.MagicMock(return_value=(mock_tzinfo,))

        with mock.patch('botocore.utils.get_tzinfo_options', mock_get_tzinfo_options):
            with self.assertRaises(RuntimeError):
                parse_timestamp(0)


class TestDatetime2Timestamp(unittest.TestCase):
    def test_datetime2timestamp_naive(self):
        self.assertEqual(
            datetime2timestamp(datetime.datetime(1970, 1, 2)), 86400)

    def test_datetime2timestamp_aware(self):
        tzinfo = tzoffset("BRST", -10800)
        self.assertEqual(
            datetime2timestamp(datetime.datetime(1970, 1, 2, tzinfo=tzinfo)),
            97200)


class TestParseToUTCDatetime(unittest.TestCase):
    def test_handles_utc_time(self):
        original = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(parse_to_aware_datetime(original), original)

    def test_handles_other_timezone(self):
        tzinfo = tzoffset("BRST", -10800)
        original = datetime.datetime(2014, 1, 1, 0, 0, 0, tzinfo=tzinfo)
        self.assertEqual(parse_to_aware_datetime(original), original)

    def test_handles_naive_datetime(self):
        original = datetime.datetime(1970, 1, 1, 0, 0, 0)
        expected = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(parse_to_aware_datetime(original), expected)

    def test_handles_string_epoch(self):
        expected = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(parse_to_aware_datetime('0'), expected)

    def test_handles_int_epoch(self):
        expected = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(parse_to_aware_datetime(0), expected)

    def test_handles_full_iso_8601(self):
        expected = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(
            parse_to_aware_datetime('1970-01-01T00:00:00Z'),
            expected)

    def test_year_only_iso_8601(self):
        expected = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzutc())
        self.assertEqual(parse_to_aware_datetime('1970-01-01'), expected)


class TestCachedProperty(unittest.TestCase):
    def test_cached_property_same_value(self):
        class CacheMe(object):
            @CachedProperty
            def foo(self):
                return 'foo'

        c = CacheMe()
        self.assertEqual(c.foo, 'foo')
        self.assertEqual(c.foo, 'foo')

    def test_cached_property_only_called_once(self):
        # Note: you would normally never want to cache
        # a property that returns a new value each time,
        # but this is done to demonstrate the caching behavior.

        class NoIncrement(object):
            def __init__(self):
                self.counter = 0

            @CachedProperty
            def current_value(self):
                self.counter += 1
                return self.counter

        c = NoIncrement()
        self.assertEqual(c.current_value, 1)
        # If the property wasn't cached, the next value should be
        # be 2, but because it's cached, we know the value will be 1.
        self.assertEqual(c.current_value, 1)


class TestArgumentGenerator(unittest.TestCase):
    def setUp(self):
        self.arg_generator = ArgumentGenerator()

    def assert_skeleton_from_model_is(self, model, generated_skeleton):
        shape = DenormalizedStructureBuilder().with_members(
            model).build_model()
        actual = self.arg_generator.generate_skeleton(shape)
        self.assertEqual(actual, generated_skeleton)

    def test_generate_string(self):
        self.assert_skeleton_from_model_is(
            model={
                'A': {'type': 'string'}
            },
            generated_skeleton={
                'A': ''
            }
        )

    def test_generate_string_enum(self):
        enum_values = ['A', 'B', 'C']
        self.assert_skeleton_from_model_is(
            model={
                'A': {'type': 'string', 'enum': enum_values}
            },
            generated_skeleton={
                'A': enum_values[0]
            }
        )

    def test_generate_scalars(self):
        self.assert_skeleton_from_model_is(
            model={
                'A': {'type': 'string'},
                'B': {'type': 'integer'},
                'C': {'type': 'float'},
                'D': {'type': 'boolean'},
                'E': {'type': 'timestamp'},
                'F': {'type': 'double'},
            },
            generated_skeleton={
                'A': '',
                'B': 0,
                'C': 0.0,
                'D': True,
                'E': datetime.datetime(1970, 1, 1, 0, 0, 0),
                'F': 0.0,
            }
        )

    def test_will_use_member_names_for_string_values(self):
        self.arg_generator = ArgumentGenerator(use_member_names=True)
        self.assert_skeleton_from_model_is(
            model={
                'A': {'type': 'string'},
                'B': {'type': 'integer'},
                'C': {'type': 'float'},
                'D': {'type': 'boolean'},
            },
            generated_skeleton={
                'A': 'A',
                'B': 0,
                'C': 0.0,
                'D': True,
            }
        )

    def test_will_use_member_names_for_string_values_of_list(self):
        self.arg_generator = ArgumentGenerator(use_member_names=True)
        # We're not using assert_skeleton_from_model_is
        # because we can't really control the name of strings shapes
        # being used in the DenormalizedStructureBuilder. We can only
        # control the name of structures and list shapes.
        shape_map = ShapeResolver({
            'InputShape': {
                'type': 'structure',
                'members': {
                    'StringList': {'shape': 'StringList'},
                }
            },
            'StringList': {
                'type': 'list',
                'member': {'shape': 'StringType'},
            },
            'StringType': {
                'type': 'string',
            }
        })
        shape = shape_map.get_shape_by_name('InputShape')
        actual = self.arg_generator.generate_skeleton(shape)

        expected = {'StringList': ['StringType']}
        self.assertEqual(actual, expected)

    def test_generate_nested_structure(self):
        self.assert_skeleton_from_model_is(
            model={
                'A': {
                    'type': 'structure',
                    'members': {
                        'B': {'type': 'string'},
                    }
                }
            },
            generated_skeleton={
                'A': {'B': ''}
            }
        )

    def test_generate_scalar_list(self):
        self.assert_skeleton_from_model_is(
            model={
                'A': {
                    'type': 'list',
                    'member': {
                        'type': 'string'
                    }
                },
            },
            generated_skeleton={
                'A': [''],
            }
        )

    def test_generate_scalar_map(self):
        self.assert_skeleton_from_model_is(
            model={
                'A': {
                    'type': 'map',
                    'key': {'type': 'string'},
                    'value':  {'type': 'string'},
                }
            },
            generated_skeleton={
                'A': {
                    'KeyName': '',
                }
            }
        )

    def test_handles_recursive_shapes(self):
        # We're not using assert_skeleton_from_model_is
        # because we can't use a DenormalizedStructureBuilder,
        # we need a normalized model to represent recursive
        # shapes.
        shape_map = ShapeResolver({
            'InputShape': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'RecursiveStruct'},
                    'B': {'shape': 'StringType'},
                }
            },
            'RecursiveStruct': {
                'type': 'structure',
                'members': {
                    'C': {'shape': 'RecursiveStruct'},
                    'D': {'shape': 'StringType'},
                }
            },
            'StringType': {
                'type': 'string',
            }
        })
        shape = shape_map.get_shape_by_name('InputShape')
        actual = self.arg_generator.generate_skeleton(shape)
        expected = {
            'A': {
                'C': {
                    # For recurisve shapes, we'll just show
                    # an empty dict.
                },
                'D': ''
            },
            'B': ''
        }
        self.assertEqual(actual, expected)


class TestChecksums(unittest.TestCase):
    def test_empty_hash(self):
        self.assertEqual(
            calculate_sha256(six.BytesIO(b''), as_hex=True),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_as_hex(self):
        self.assertEqual(
            calculate_sha256(six.BytesIO(b'hello world'), as_hex=True),
            'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')

    def test_as_binary(self):
        self.assertEqual(
            calculate_sha256(six.BytesIO(b'hello world'), as_hex=False),
            (b"\xb9M'\xb9\x93M>\x08\xa5.R\xd7\xda}\xab\xfa\xc4\x84\xef"
             b"\xe3zS\x80\xee\x90\x88\xf7\xac\xe2\xef\xcd\xe9"))


class TestTreeHash(unittest.TestCase):
    # Note that for these tests I've independently verified
    # what the expected tree hashes should be from other
    # SDK implementations.

    def test_empty_tree_hash(self):
        self.assertEqual(
            calculate_tree_hash(six.BytesIO(b'')),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_tree_hash_less_than_one_mb(self):
        one_k = six.BytesIO(b'a' * 1024)
        self.assertEqual(
            calculate_tree_hash(one_k),
            '2edc986847e209b4016e141a6dc8716d3207350f416969382d431539bf292e4a')

    def test_tree_hash_exactly_one_mb(self):
        one_meg_bytestring = b'a' * (1 * 1024 * 1024)
        one_meg = six.BytesIO(one_meg_bytestring)
        self.assertEqual(
            calculate_tree_hash(one_meg),
            '9bc1b2a288b26af7257a36277ae3816a7d4f16e89c1e7e77d0a5c48bad62b360')

    def test_tree_hash_multiple_of_one_mb(self):
        four_mb = six.BytesIO(b'a' * (4 * 1024 * 1024))
        self.assertEqual(
            calculate_tree_hash(four_mb),
            '9491cb2ed1d4e7cd53215f4017c23ec4ad21d7050a1e6bb636c4f67e8cddb844')

    def test_tree_hash_offset_of_one_mb_multiple(self):
        offset_four_mb = six.BytesIO(b'a' * (4 * 1024 * 1024) + b'a' * 20)
        self.assertEqual(
            calculate_tree_hash(offset_four_mb),
            '12f3cbd6101b981cde074039f6f728071da8879d6f632de8afc7cdf00661b08f')


class TestIsValidEndpointURL(unittest.TestCase):
    def test_dns_name_is_valid(self):
        self.assertTrue(is_valid_endpoint_url('https://s3.amazonaws.com/'))

    def test_ip_address_is_allowed(self):
        self.assertTrue(is_valid_endpoint_url('https://10.10.10.10/'))

    def test_path_component_ignored(self):
        self.assertTrue(
            is_valid_endpoint_url('https://foo.bar.com/other/path/'))

    def test_can_have_port(self):
        self.assertTrue(is_valid_endpoint_url('https://foo.bar.com:12345/'))

    def test_ip_can_have_port(self):
        self.assertTrue(is_valid_endpoint_url('https://10.10.10.10:12345/'))

    def test_cannot_have_spaces(self):
        self.assertFalse(is_valid_endpoint_url('https://my invalid name/'))

    def test_missing_scheme(self):
        self.assertFalse(is_valid_endpoint_url('foo.bar.com'))

    def test_no_new_lines(self):
        self.assertFalse(is_valid_endpoint_url('https://foo.bar.com\nbar/'))

    def test_long_hostname(self):
        long_hostname = 'htps://%s.com' % ('a' * 256)
        self.assertFalse(is_valid_endpoint_url(long_hostname))

    def test_hostname_can_end_with_dot(self):
        self.assertTrue(is_valid_endpoint_url('https://foo.bar.com./'))

    def test_hostname_no_dots(self):
        self.assertTrue(is_valid_endpoint_url('https://foo/'))


class TestFixS3Host(unittest.TestCase):
    def test_fix_s3_host_initial(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://s3-us-west-2.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name)
        self.assertEqual(request.url,
                         'https://bucket.s3-us-west-2.amazonaws.com/key.txt')
        self.assertEqual(request.auth_path, '/bucket/key.txt')

    def test_fix_s3_host_only_applied_once(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://s3.us-west-2.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name)
        # Calling the handler again should not affect the end result:
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name)
        self.assertEqual(request.url,
                         'https://bucket.s3.us-west-2.amazonaws.com/key.txt')
        # This was a bug previously.  We want to make sure that
        # calling fix_s3_host() again does not alter the auth_path.
        # Otherwise we'll get signature errors.
        self.assertEqual(request.auth_path, '/bucket/key.txt')

    def test_dns_style_not_used_for_get_bucket_location(self):
        original_url = 'https://s3-us-west-2.amazonaws.com/bucket?location'
        request = AWSRequest(
            method='GET', headers={},
            url=original_url,
        )
        signature_version = 's3'
        region_name = 'us-west-2'
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name)
        # The request url should not have been modified because this is
        # a request for GetBucketLocation.
        self.assertEqual(request.url, original_url)

    def test_can_provide_default_endpoint_url(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://s3-us-west-2.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name,
            default_endpoint_url='foo.s3.amazonaws.com')
        self.assertEqual(request.url,
                         'https://bucket.foo.s3.amazonaws.com/key.txt')

    def test_no_endpoint_url_uses_request_url(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://s3-us-west-2.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        fix_s3_host(
            request=request, signature_version=signature_version,
            region_name=region_name,
            # A value of None means use the url in the current request.
            default_endpoint_url=None,
        )
        self.assertEqual(request.url,
                         'https://bucket.s3-us-west-2.amazonaws.com/key.txt')


class TestSwitchToVirtualHostStyle(unittest.TestCase):
    def test_switch_to_virtual_host_style(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        self.assertEqual(request.url,
                         'https://bucket.foo.amazonaws.com/key.txt')
        self.assertEqual(request.auth_path, '/bucket/key.txt')

    def test_uses_default_endpoint(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name, default_endpoint_url='s3.amazonaws.com')
        self.assertEqual(request.url,
                         'https://bucket.s3.amazonaws.com/key.txt')
        self.assertEqual(request.auth_path, '/bucket/key.txt')

    def test_throws_invalid_dns_name_error(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/mybucket.foo/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        with self.assertRaises(InvalidDNSNameError):
            switch_to_virtual_host_style(
                request=request, signature_version=signature_version,
                region_name=region_name)

    def test_fix_s3_host_only_applied_once(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        # Calling the handler again should not affect the end result:
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        self.assertEqual(request.url,
                         'https://bucket.foo.amazonaws.com/key.txt')
        # This was a bug previously.  We want to make sure that
        # calling fix_s3_host() again does not alter the auth_path.
        # Otherwise we'll get signature errors.
        self.assertEqual(request.auth_path, '/bucket/key.txt')

    def test_virtual_host_style_for_make_bucket(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/bucket'
        )
        region_name = 'us-west-2'
        signature_version = 's3'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        self.assertEqual(request.url,
                         'https://bucket.foo.amazonaws.com/')

    def test_virtual_host_style_not_used_for_get_bucket_location(self):
        original_url = 'https://foo.amazonaws.com/bucket?location'
        request = AWSRequest(
            method='GET', headers={},
            url=original_url,
        )
        signature_version = 's3'
        region_name = 'us-west-2'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        # The request url should not have been modified because this is
        # a request for GetBucketLocation.
        self.assertEqual(request.url, original_url)

    def test_virtual_host_style_not_used_for_list_buckets(self):
        original_url = 'https://foo.amazonaws.com/'
        request = AWSRequest(
            method='GET', headers={},
            url=original_url,
        )
        signature_version = 's3'
        region_name = 'us-west-2'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name)
        # The request url should not have been modified because this is
        # a request for GetBucketLocation.
        self.assertEqual(request.url, original_url)

    def test_is_unaffected_by_sigv4(self):
        request = AWSRequest(
            method='PUT', headers={},
            url='https://foo.amazonaws.com/bucket/key.txt'
        )
        region_name = 'us-west-2'
        signature_version = 's3v4'
        switch_to_virtual_host_style(
            request=request, signature_version=signature_version,
            region_name=region_name, default_endpoint_url='s3.amazonaws.com')
        self.assertEqual(request.url,
                         'https://bucket.s3.amazonaws.com/key.txt')


class TestSwitchToChunkedEncodingForNonSeekableObjects(unittest.TestCase):
    def test_switch_to_chunked_encodeing_for_stream_like_object(self):
        request = AWSRequest(
            method='POST', headers={},
            data=io.BufferedIOBase(b"some initial binary data"),
            url='https://foo.amazonaws.com/bucket/key.txt'
        )
        prepared_request = request.prepare()
        self.assertEqual(
            prepared_request.headers, {'Transfer-Encoding': 'chunked'}
        )


class TestInstanceCache(unittest.TestCase):
    class DummyClass(object):
        def __init__(self, cache):
            self._instance_cache = cache

        @instance_cache
        def add(self, x, y):
            return x + y

        @instance_cache
        def sub(self, x, y):
            return x - y

    def setUp(self):
        self.cache = {}

    def test_cache_single_method_call(self):
        adder = self.DummyClass(self.cache)
        self.assertEqual(adder.add(2, 1), 3)
        # This should result in one entry in the cache.
        self.assertEqual(len(self.cache), 1)
        # When we call the method with the same args,
        # we should reuse the same entry in the cache.
        self.assertEqual(adder.add(2, 1), 3)
        self.assertEqual(len(self.cache), 1)

    def test_can_cache_multiple_methods(self):
        adder = self.DummyClass(self.cache)
        adder.add(2, 1)

        # A different method results in a new cache entry,
        # so now there should be two elements in the cache.
        self.assertEqual(adder.sub(2, 1), 1)
        self.assertEqual(len(self.cache), 2)
        self.assertEqual(adder.sub(2, 1), 1)

    def test_can_cache_kwargs(self):
        adder = self.DummyClass(self.cache)
        adder.add(x=2, y=1)
        self.assertEqual(adder.add(x=2, y=1), 3)
        self.assertEqual(len(self.cache), 1)


class TestMergeDicts(unittest.TestCase):
    def test_merge_dicts_overrides(self):
        first = {
            'foo': {'bar': {'baz': {'one': 'ORIGINAL', 'two': 'ORIGINAL'}}}}
        second = {'foo': {'bar': {'baz': {'one': 'UPDATE'}}}}

        merge_dicts(first, second)
        # The value from the second dict wins.
        self.assertEqual(first['foo']['bar']['baz']['one'], 'UPDATE')
        # And we still preserve the other attributes.
        self.assertEqual(first['foo']['bar']['baz']['two'], 'ORIGINAL')

    def test_merge_dicts_new_keys(self):
        first = {
            'foo': {'bar': {'baz': {'one': 'ORIGINAL', 'two': 'ORIGINAL'}}}}
        second = {'foo': {'bar': {'baz': {'three': 'UPDATE'}}}}

        merge_dicts(first, second)
        self.assertEqual(first['foo']['bar']['baz']['one'], 'ORIGINAL')
        self.assertEqual(first['foo']['bar']['baz']['two'], 'ORIGINAL')
        self.assertEqual(first['foo']['bar']['baz']['three'], 'UPDATE')

    def test_merge_empty_dict_does_nothing(self):
        first = {'foo': {'bar': 'baz'}}
        merge_dicts(first, {})
        self.assertEqual(first, {'foo': {'bar': 'baz'}})

    def test_more_than_one_sub_dict(self):
        first = {'one': {'inner': 'ORIGINAL', 'inner2': 'ORIGINAL'},
                 'two': {'inner': 'ORIGINAL', 'inner2': 'ORIGINAL'}}
        second = {'one': {'inner': 'UPDATE'}, 'two': {'inner': 'UPDATE'}}

        merge_dicts(first, second)
        self.assertEqual(first['one']['inner'], 'UPDATE')
        self.assertEqual(first['one']['inner2'], 'ORIGINAL')

        self.assertEqual(first['two']['inner'], 'UPDATE')
        self.assertEqual(first['two']['inner2'], 'ORIGINAL')

    def test_new_keys(self):
        first = {'one': {'inner': 'ORIGINAL'}, 'two': {'inner': 'ORIGINAL'}}
        second = {'three': {'foo': {'bar': 'baz'}}}
        # In this case, second has no keys in common, but we'd still expect
        # this to get merged.
        merge_dicts(first, second)
        self.assertEqual(first['three']['foo']['bar'], 'baz')

    def test_list_values_no_append(self):
        dict1 = {'Foo': ['old_foo_value']}
        dict2 = {'Foo': ['new_foo_value']}
        merge_dicts(dict1, dict2)
        self.assertEqual(
            dict1, {'Foo': ['new_foo_value']})

    def test_list_values_append(self):
        dict1 = {'Foo': ['old_foo_value']}
        dict2 = {'Foo': ['new_foo_value']}
        merge_dicts(dict1, dict2, append_lists=True)
        self.assertEqual(
            dict1, {'Foo': ['old_foo_value', 'new_foo_value']})

    def test_list_values_mismatching_types(self):
        dict1 = {'Foo': 'old_foo_value'}
        dict2 = {'Foo': ['new_foo_value']}
        merge_dicts(dict1, dict2, append_lists=True)
        self.assertEqual(
            dict1, {'Foo': ['new_foo_value']})

    def test_list_values_missing_key(self):
        dict1 = {}
        dict2 = {'Foo': ['foo_value']}
        merge_dicts(dict1, dict2, append_lists=True)
        self.assertEqual(
            dict1, {'Foo': ['foo_value']})


class TestLowercaseDict(unittest.TestCase):
    def test_lowercase_dict_empty(self):
        original = {}
        copy = lowercase_dict(original)
        self.assertEqual(original, copy)

    def test_lowercase_dict_original_keys_lower(self):
        original = {
            'lower_key1': 1,
            'lower_key2': 2,
        }
        copy = lowercase_dict(original)
        self.assertEqual(original, copy)

    def test_lowercase_dict_original_keys_mixed(self):
        original = {
            'SOME_KEY': 'value',
            'AnOTher_OnE': 'anothervalue',
        }
        copy = lowercase_dict(original)
        expected = {
            'some_key': 'value',
            'another_one': 'anothervalue',
        }
        self.assertEqual(expected, copy)


class TestGetServiceModuleName(unittest.TestCase):
    def setUp(self):
        self.service_description = {
            'metadata': {
                'serviceFullName': 'AWS MyService',
                'apiVersion': '2014-01-01',
                'endpointPrefix': 'myservice',
                'signatureVersion': 'v4',
                'protocol': 'query'
            },
            'operations': {},
            'shapes': {},
        }
        self.service_model = ServiceModel(
            self.service_description, 'myservice')

    def test_default(self):
        self.assertEqual(
            get_service_module_name(self.service_model),
            'MyService'
        )

    def test_client_name_with_amazon(self):
        self.service_description['metadata']['serviceFullName'] = (
            'Amazon MyService')
        self.assertEqual(
            get_service_module_name(self.service_model),
            'MyService'
        )

    def test_client_name_using_abreviation(self):
        self.service_description['metadata']['serviceAbbreviation'] = (
            'Abbreviation')
        self.assertEqual(
            get_service_module_name(self.service_model),
            'Abbreviation'
        )

    def test_client_name_with_non_alphabet_characters(self):
        self.service_description['metadata']['serviceFullName'] = (
            'Amazon My-Service')
        self.assertEqual(
            get_service_module_name(self.service_model),
            'MyService'
        )

    def test_client_name_with_no_full_name_or_abbreviation(self):
        del self.service_description['metadata']['serviceFullName']
        self.assertEqual(
            get_service_module_name(self.service_model),
            'myservice'
        )


class TestPercentEncodeSequence(unittest.TestCase):
    def test_percent_encode_empty(self):
        self.assertEqual(percent_encode_sequence({}), '')

    def test_percent_encode_special_chars(self):
        self.assertEqual(
            percent_encode_sequence({'k1': 'with spaces++/'}),
            'k1=with%20spaces%2B%2B%2F')

    def test_percent_encode_string_string_tuples(self):
        self.assertEqual(percent_encode_sequence([('k1', 'v1'), ('k2', 'v2')]),
                         'k1=v1&k2=v2')

    def test_percent_encode_dict_single_pair(self):
        self.assertEqual(percent_encode_sequence({'k1': 'v1'}), 'k1=v1')

    def test_percent_encode_dict_string_string(self):
        self.assertEqual(
            percent_encode_sequence(OrderedDict([('k1', 'v1'), ('k2', 'v2')])),
                                    'k1=v1&k2=v2')

    def test_percent_encode_single_list_of_values(self):
        self.assertEqual(percent_encode_sequence({'k1': ['a', 'b', 'c']}),
                         'k1=a&k1=b&k1=c')

    def test_percent_encode_list_values_of_string(self):
        self.assertEqual(
            percent_encode_sequence(
                OrderedDict([('k1', ['a', 'list']),
                             ('k2', ['another', 'list'])])),
            'k1=a&k1=list&k2=another&k2=list')

class TestPercentEncode(unittest.TestCase):
    def test_percent_encode_obj(self):
        self.assertEqual(percent_encode(1), '1')

    def test_percent_encode_text(self):
        self.assertEqual(percent_encode(u''), '')
        self.assertEqual(percent_encode(u'a'), 'a')
        self.assertEqual(percent_encode(u'\u0000'), '%00')
        # Codepoint > 0x7f
        self.assertEqual(percent_encode(u'\u2603'), '%E2%98%83')
        # Codepoint > 0xffff
        self.assertEqual(percent_encode(u'\U0001f32e'), '%F0%9F%8C%AE')

    def test_percent_encode_bytes(self):
        self.assertEqual(percent_encode(b''), '')
        self.assertEqual(percent_encode(b'a'), u'a')
        self.assertEqual(percent_encode(b'\x00'), u'%00')
        # UTF-8 Snowman
        self.assertEqual(percent_encode(b'\xe2\x98\x83'), '%E2%98%83')
        # Arbitrary bytes (not valid UTF-8).
        self.assertEqual(percent_encode(b'\x80\x00'), '%80%00')

class TestSwitchHostS3Accelerate(unittest.TestCase):
    def setUp(self):
        self.original_url = 'https://s3.amazonaws.com/foo/key.txt'
        self.request = AWSRequest(
            method='PUT', headers={},
            url=self.original_url
        )
        self.client_config = Config()
        self.request.context['client_config'] = self.client_config

    def test_switch_host(self):
        switch_host_s3_accelerate(self.request, 'PutObject')
        self.assertEqual(
            self.request.url,
            'https://s3-accelerate.amazonaws.com/foo/key.txt')

    def test_do_not_switch_black_listed_operations(self):
        # It should not get switched for ListBuckets, DeleteBucket, and
        # CreateBucket
        blacklist_ops = [
            'ListBuckets',
            'DeleteBucket',
            'CreateBucket'
        ]
        for op_name in blacklist_ops:
            switch_host_s3_accelerate(self.request, op_name)
            self.assertEqual(self.request.url, self.original_url)

    def test_uses_original_endpoint_scheme(self):
        self.request.url = 'http://s3.amazonaws.com/foo/key.txt'
        switch_host_s3_accelerate(self.request, 'PutObject')
        self.assertEqual(
            self.request.url,
            'http://s3-accelerate.amazonaws.com/foo/key.txt')

    def test_uses_dualstack(self):
        self.client_config.s3 = {'use_dualstack_endpoint': True}
        self.original_url = 'https://s3.dualstack.amazonaws.com/foo/key.txt'
        self.request = AWSRequest(
            method='PUT', headers={},
            url=self.original_url
        )
        self.request.context['client_config'] = self.client_config
        switch_host_s3_accelerate(self.request, 'PutObject')
        self.assertEqual(
            self.request.url,
            'https://s3-accelerate.dualstack.amazonaws.com/foo/key.txt')


class TestDeepMerge(unittest.TestCase):
    def test_simple_merge(self):
        a = {'key': 'value'}
        b = {'otherkey': 'othervalue'}
        deep_merge(a, b)

        expected = {'key': 'value', 'otherkey': 'othervalue'}
        self.assertEqual(a, expected)

    def test_merge_list(self):
        # Lists are treated as opaque data and so no effort should be made to
        # combine them.
        a = {'key': ['original']}
        b = {'key': ['new']}
        deep_merge(a, b)
        self.assertEqual(a, {'key': ['new']})

    def test_merge_number(self):
        # The value from b is always taken
        a = {'key': 10}
        b = {'key': 45}
        deep_merge(a, b)
        self.assertEqual(a, {'key': 45})

        a = {'key': 45}
        b = {'key': 10}
        deep_merge(a, b)
        self.assertEqual(a, {'key': 10})

    def test_merge_boolean(self):
        # The value from b is always taken
        a = {'key': False}
        b = {'key': True}
        deep_merge(a, b)
        self.assertEqual(a, {'key': True})

        a = {'key': True}
        b = {'key': False}
        deep_merge(a, b)
        self.assertEqual(a, {'key': False})

    def test_merge_string(self):
        a = {'key': 'value'}
        b = {'key': 'othervalue'}
        deep_merge(a, b)
        self.assertEqual(a, {'key': 'othervalue'})

    def test_merge_overrides_value(self):
        # The value from b is always taken, even when it's a different type
        a = {'key': 'original'}
        b = {'key': {'newkey': 'newvalue'}}
        deep_merge(a, b)
        self.assertEqual(a, {'key': {'newkey': 'newvalue'}})

        a = {'key': {'anotherkey': 'value'}}
        b = {'key': 'newvalue'}
        deep_merge(a, b)
        self.assertEqual(a, {'key': 'newvalue'})

    def test_deep_merge(self):
        a = {
            'first': {
                'second': {
                    'key': 'value',
                    'otherkey': 'othervalue'
                },
                'key': 'value'
            }
        }
        b = {
            'first': {
                'second': {
                    'otherkey': 'newvalue',
                    'yetanotherkey': 'yetanothervalue'
                }
            }
        }
        deep_merge(a, b)

        expected = {
            'first': {
                'second': {
                    'key': 'value',
                    'otherkey': 'newvalue',
                    'yetanotherkey': 'yetanothervalue'
                },
                'key': 'value'
            }
        }
        self.assertEqual(a, expected)


class TestS3RegionRedirector(unittest.TestCase):
    def setUp(self):
        self.endpoint_bridge = mock.Mock()
        self.endpoint_bridge.resolve.return_value = {
            'endpoint_url': 'https://eu-central-1.amazonaws.com'
        }
        self.client = mock.Mock()
        self.cache = {}
        self.redirector = S3RegionRedirector(self.endpoint_bridge, self.client)
        self.set_client_response_headers({})
        self.operation = mock.Mock()
        self.operation.name = 'foo'

    def set_client_response_headers(self, headers):
        error_response = ClientError({
            'Error': {
                'Code': '',
                'Message': ''
            },
            'ResponseMetadata': {
                'HTTPHeaders': headers
            }
        }, 'HeadBucket')
        success_response = {
            'ResponseMetadata': {
                'HTTPHeaders': headers
            }
        }
        self.client.head_bucket.side_effect = [
            error_response, success_response]

    def test_set_request_url(self):
        params = {'url': 'https://us-west-2.amazonaws.com/foo'}
        context = {'signing': {
            'endpoint': 'https://eu-central-1.amazonaws.com'
        }}
        self.redirector.set_request_url(params, context)
        self.assertEqual(
            params['url'], 'https://eu-central-1.amazonaws.com/foo')

    def test_only_changes_request_url_if_endpoint_present(self):
        params = {'url': 'https://us-west-2.amazonaws.com/foo'}
        context = {}
        self.redirector.set_request_url(params, context)
        self.assertEqual(
            params['url'], 'https://us-west-2.amazonaws.com/foo')

    def test_set_request_url_keeps_old_scheme(self):
        params = {'url': 'http://us-west-2.amazonaws.com/foo'}
        context = {'signing': {
            'endpoint': 'https://eu-central-1.amazonaws.com'
        }}
        self.redirector.set_request_url(params, context)
        self.assertEqual(
            params['url'], 'http://eu-central-1.amazonaws.com/foo')

    def test_sets_signing_context_from_cache(self):
        signing_context = {'endpoint': 'bar'}
        self.cache['foo'] = signing_context
        self.redirector = S3RegionRedirector(
            self.endpoint_bridge, self.client, cache=self.cache)
        params = {'Bucket': 'foo'}
        context = {}
        self.redirector.redirect_from_cache(params, context)
        self.assertEqual(context.get('signing'), signing_context)

    def test_only_changes_context_if_bucket_in_cache(self):
        signing_context = {'endpoint': 'bar'}
        self.cache['bar'] = signing_context
        self.redirector = S3RegionRedirector(
            self.endpoint_bridge, self.client, cache=self.cache)
        params = {'Bucket': 'foo'}
        context = {}
        self.redirector.redirect_from_cache(params, context)
        self.assertNotEqual(context.get('signing'), signing_context)

    def test_redirect_from_error(self):
        request_dict = {
            'context': {'signing': {'bucket': 'foo'}},
            'url': 'https://us-west-2.amazonaws.com/foo'
        }
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo'
            },
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        })

        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)

        # The response needs to be 0 so that there is no retry delay
        self.assertEqual(redirect_response, 0)

        self.assertEqual(
            request_dict['url'], 'https://eu-central-1.amazonaws.com/foo')

        expected_signing_context = {
            'endpoint': 'https://eu-central-1.amazonaws.com',
            'bucket': 'foo',
            'region': 'eu-central-1'
        }
        signing_context = request_dict['context'].get('signing')
        self.assertEqual(signing_context, expected_signing_context)
        self.assertTrue(request_dict['context'].get('s3_redirected'))

    def test_does_not_redirect_if_previously_redirected(self):
        request_dict = {
            'context': {
                'signing': {'bucket': 'foo', 'region': 'us-west-2'},
                's3_redirected': True,
            },
            'url': 'https://us-west-2.amazonaws.com/foo'
        }
        response = (None, {
            'Error': {
                'Code': '400',
                'Message': 'Bad Request',
            },
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'us-west-2'}
            }
        })
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertIsNone(redirect_response)

    def test_does_not_redirect_unless_permanentredirect_recieved(self):
        request_dict = {}
        response = (None, {})
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertIsNone(redirect_response)
        self.assertEqual(request_dict, {})

    def test_does_not_redirect_if_region_cannot_be_found(self):
        request_dict = {'url': 'https://us-west-2.amazonaws.com/foo',
                        'context': {'signing': {'bucket': 'foo'}}}
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo'
            },
            'ResponseMetadata': {
                'HTTPHeaders': {}
            }
        })

        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)

        self.assertIsNone(redirect_response)

    def test_redirects_301(self):
        request_dict = {'url': 'https://us-west-2.amazonaws.com/foo',
                        'context': {'signing': {'bucket': 'foo'}}}
        response = (None, {
            'Error': {
                'Code': '301',
                'Message': 'Moved Permanently'
            },
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        })

        self.operation.name = 'HeadObject'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertEqual(redirect_response, 0)

        self.operation.name = 'ListObjects'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertIsNone(redirect_response)

    def test_redirects_400_head_bucket(self):
        request_dict = {'url': 'https://us-west-2.amazonaws.com/foo',
                        'context': {'signing': {'bucket': 'foo'}}}
        response = (None, {
            'Error': {'Code': '400', 'Message': 'Bad Request'},
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        })

        self.operation.name = 'HeadObject'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertEqual(redirect_response, 0)

        self.operation.name = 'ListObjects'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertIsNone(redirect_response)

    def test_does_not_redirect_400_head_bucket_no_region_header(self):
        # We should not redirect a 400 Head* if the region header is not
        # present as this will lead to infinitely calling HeadBucket.
        request_dict = {'url': 'https://us-west-2.amazonaws.com/foo',
                        'context': {'signing': {'bucket': 'foo'}}}
        response = (None, {
            'Error': {'Code': '400', 'Message': 'Bad Request'},
            'ResponseMetadata': {
                'HTTPHeaders': {}
            }
        })

        self.operation.name = 'HeadBucket'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        head_bucket_calls = self.client.head_bucket.call_count
        self.assertIsNone(redirect_response)
        # We should not have made an additional head bucket call
        self.assertEqual(head_bucket_calls, 0)

    def test_does_not_redirect_if_None_response(self):
        request_dict = {'url': 'https://us-west-2.amazonaws.com/foo',
                        'context': {'signing': {'bucket': 'foo'}}}
        response = None
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertIsNone(redirect_response)

    def test_get_region_from_response(self):
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo'
            },
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        })
        region = self.redirector.get_bucket_region('foo', response)
        self.assertEqual(region, 'eu-central-1')

    def test_get_region_from_response_error_body(self):
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo',
                'Region': 'eu-central-1'
            },
            'ResponseMetadata': {
                'HTTPHeaders': {}
            }
        })
        region = self.redirector.get_bucket_region('foo', response)
        self.assertEqual(region, 'eu-central-1')

    def test_get_region_from_head_bucket_error(self):
        self.set_client_response_headers(
            {'x-amz-bucket-region': 'eu-central-1'})
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo',
            },
            'ResponseMetadata': {
                'HTTPHeaders': {}
            }
        })
        region = self.redirector.get_bucket_region('foo', response)
        self.assertEqual(region, 'eu-central-1')

    def test_get_region_from_head_bucket_success(self):
        success_response = {
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        }
        self.client.head_bucket.side_effect = None
        self.client.head_bucket.return_value = success_response
        response = (None, {
            'Error': {
                'Code': 'PermanentRedirect',
                'Endpoint': 'foo.eu-central-1.amazonaws.com',
                'Bucket': 'foo',
            },
            'ResponseMetadata': {
                'HTTPHeaders': {}
            }
        })
        region = self.redirector.get_bucket_region('foo', response)
        self.assertEqual(region, 'eu-central-1')

    def test_no_redirect_from_error_for_accesspoint(self):
        request_dict = {
            'url': (
                'https://myendpoint-123456789012.s3-accesspoint.'
                'us-west-2.amazonaws.com/key'
            ),
            'context': {
                's3_accesspoint': {}
            }
        }
        response = (None, {
            'Error': {'Code': '400', 'Message': 'Bad Request'},
            'ResponseMetadata': {
                'HTTPHeaders': {'x-amz-bucket-region': 'eu-central-1'}
            }
        })

        self.operation.name = 'HeadObject'
        redirect_response = self.redirector.redirect_from_error(
            request_dict, response, self.operation)
        self.assertEqual(redirect_response, None)

    def test_no_redirect_from_cache_for_accesspoint(self):
        self.cache['foo'] = {'endpoint': 'foo-endpoint'}
        self.redirector = S3RegionRedirector(
            self.endpoint_bridge, self.client, cache=self.cache)
        params = {'Bucket': 'foo'}
        context = {'s3_accesspoint': {}}
        self.redirector.redirect_from_cache(params, context)
        self.assertNotIn('signing', context)


class TestArnParser(unittest.TestCase):
    def setUp(self):
        self.parser = ArnParser()

    def test_parse(self):
        arn = 'arn:aws:s3:us-west-2:1023456789012:myresource'
        self.assertEqual(
            self.parser.parse_arn(arn),
            {
                'partition': 'aws',
                'service': 's3',
                'region': 'us-west-2',
                'account': '1023456789012',
                'resource': 'myresource',
            }
        )

    def test_parse_invalid_arn(self):
        with self.assertRaises(InvalidArnException):
            self.parser.parse_arn('arn:aws:s3')

    def test_parse_arn_with_resource_type(self):
        arn = 'arn:aws:s3:us-west-2:1023456789012:bucket_name:mybucket'
        self.assertEqual(
            self.parser.parse_arn(arn),
            {
                'partition': 'aws',
                'service': 's3',
                'region': 'us-west-2',
                'account': '1023456789012',
                'resource': 'bucket_name:mybucket',
            }
        )

    def test_parse_arn_with_empty_elements(self):
        arn = 'arn:aws:s3:::mybucket'
        self.assertEqual(
            self.parser.parse_arn(arn),
            {
                'partition': 'aws',
                'service': 's3',
                'region': '',
                'account': '',
                'resource': 'mybucket',
            }
        )


class TestS3ArnParamHandler(unittest.TestCase):
    def setUp(self):
        self.arn_handler = S3ArnParamHandler()
        self.model = mock.Mock(OperationModel)
        self.model.name = 'GetObject'

    def test_register(self):
        event_emitter = mock.Mock()
        self.arn_handler.register(event_emitter)
        event_emitter.register.assert_called_with(
            'before-parameter-build.s3', self.arn_handler.handle_arn)

    def test_accesspoint_arn(self):
        params = {
            'Bucket': 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint'
        }
        context = {}
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': 'endpoint'})
        self.assertEqual(
            context,
            {
                's3_accesspoint': {
                    'name': 'endpoint',
                    'account': '123456789012',
                    'region': 'us-west-2',
                    'partition': 'aws',
                    'service': 's3',
                }
            }
        )

    def test_accesspoint_arn_with_colon(self):
        params = {
            'Bucket': 'arn:aws:s3:us-west-2:123456789012:accesspoint:endpoint'
        }
        context = {}
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': 'endpoint'})
        self.assertEqual(
            context,
            {
                's3_accesspoint': {
                    'name': 'endpoint',
                    'account': '123456789012',
                    'region': 'us-west-2',
                    'partition': 'aws',
                    'service': 's3',
                }
            }
        )

    def test_errors_for_non_accesspoint_arn(self):
        params = {
            'Bucket': 'arn:aws:s3:us-west-2:123456789012:unsupported:resource'
        }
        context = {}
        with self.assertRaises(UnsupportedS3ArnError):
            self.arn_handler.handle_arn(params, self.model, context)

    def test_outpost_arn_with_colon(self):
        params = {
            'Bucket': (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
                'op-01234567890123456:accesspoint:myaccesspoint'
            )
        }
        context = {}
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': 'myaccesspoint'})
        self.assertEqual(
            context,
            {
                's3_accesspoint': {
                    'name': 'myaccesspoint',
                    'outpost_name': 'op-01234567890123456',
                    'account': '123456789012',
                    'region': 'us-west-2',
                    'partition': 'aws',
                    'service': 's3-outposts',
                }
            }
        )

    def test_outpost_arn_with_slash(self):
        params = {
            'Bucket': (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/'
                'op-01234567890123456/accesspoint/myaccesspoint'
            )
        }
        context = {}
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': 'myaccesspoint'})
        self.assertEqual(
            context,
            {
                's3_accesspoint': {
                    'name': 'myaccesspoint',
                    'outpost_name': 'op-01234567890123456',
                    'account': '123456789012',
                    'region': 'us-west-2',
                    'partition': 'aws',
                    'service': 's3-outposts',
                }
            }
        )

    def test_outpost_arn_errors_for_missing_fields(self):
        params = {
            'Bucket': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost/'
            'op-01234567890123456/accesspoint'
        }
        with self.assertRaises(UnsupportedOutpostResourceError):
            self.arn_handler.handle_arn(params, self.model, {})

    def test_outpost_arn_errors_for_empty_fields(self):
        params = {
            'Bucket': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost/'
            '/accesspoint/myaccesspoint'
        }
        with self.assertRaises(UnsupportedOutpostResourceError):
            self.arn_handler.handle_arn(params, self.model, {})

    def test_ignores_bucket_names(self):
        params = {'Bucket': 'mybucket'}
        context = {}
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': 'mybucket'})
        self.assertEqual(context, {})

    def test_ignores_create_bucket(self):
        arn = 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint'
        params = {'Bucket': arn}
        context = {}
        self.model.name = 'CreateBucket'
        self.arn_handler.handle_arn(params, self.model, context)
        self.assertEqual(params, {'Bucket': arn})
        self.assertEqual(context, {})


class TestS3EndpointSetter(unittest.TestCase):
    def setUp(self):
        self.operation_name = 'GetObject'
        self.signature_version = 's3v4'
        self.region_name = 'us-west-2'
        self.service = 's3'
        self.account = '123456789012'
        self.bucket = 'mybucket'
        self.key = 'key.txt'
        self.accesspoint_name = 'myaccesspoint'
        self.outpost_name = 'op-123456789012'
        self.partition = 'aws'
        self.endpoint_resolver = mock.Mock()
        self.dns_suffix = 'amazonaws.com'
        self.endpoint_resolver.construct_endpoint.return_value = {
            'dnsSuffix': self.dns_suffix
        }
        self.endpoint_setter = self.get_endpoint_setter()

    def get_endpoint_setter(self, **kwargs):
        setter_kwargs = {
            'endpoint_resolver': self.endpoint_resolver,
            'region': self.region_name,
        }
        setter_kwargs.update(kwargs)
        return S3EndpointSetter(**setter_kwargs)

    def get_s3_request(self, bucket=None, key=None, scheme='https://',
                       querystring=None):
        url = scheme + 's3.us-west-2.amazonaws.com/'
        if bucket:
            url += bucket
        if key:
            url += '/%s' % key
        if querystring:
            url += '?%s' % querystring
        return AWSRequest(method='GET', headers={}, url=url)

    def get_s3_outpost_request(self, **s3_request_kwargs):
        request = self.get_s3_request(
            self.accesspoint_name, **s3_request_kwargs)
        accesspoint_context = self.get_s3_accesspoint_context(
            name=self.accesspoint_name, outpost_name=self.outpost_name)
        request.context['s3_accesspoint'] = accesspoint_context
        return request

    def get_s3_accesspoint_request(self, accesspoint_name=None,
                                   accesspoint_context=None,
                                   **s3_request_kwargs):
        if not accesspoint_name:
            accesspoint_name = self.accesspoint_name
        request = self.get_s3_request(accesspoint_name, **s3_request_kwargs)
        if accesspoint_context is None:
            accesspoint_context = self.get_s3_accesspoint_context(
                name=accesspoint_name)
        request.context['s3_accesspoint'] = accesspoint_context
        return request

    def get_s3_accesspoint_context(self, **overrides):
        accesspoint_context = {
            'name': self.accesspoint_name,
            'account': self.account,
            'region': self.region_name,
            'partition': self.partition,
            'service': self.service,
        }
        accesspoint_context.update(overrides)
        return accesspoint_context

    def call_set_endpoint(self, endpoint_setter, request, **kwargs):
        set_endpoint_kwargs = {
            'request': request,
            'operation_name': self.operation_name,
            'signature_version': self.signature_version,
            'region_name': self.region_name,
        }
        set_endpoint_kwargs.update(kwargs)
        endpoint_setter.set_endpoint(**set_endpoint_kwargs)

    def test_register(self):
        event_emitter = mock.Mock()
        self.endpoint_setter.register(event_emitter)
        event_emitter.register.assert_has_calls([
            mock.call('before-sign.s3', self.endpoint_setter.set_endpoint),
            mock.call('choose-signer.s3', self.endpoint_setter.set_signer),
            mock.call(
                'before-call.s3.WriteGetObjectResponse',
                self.endpoint_setter.update_endpoint_to_s3_object_lambda,
            )
        ])

    def test_outpost_endpoint(self):
        request = self.get_s3_outpost_request()
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.%s.s3-outposts.%s.amazonaws.com/' % (
            self.accesspoint_name, self.account, self.outpost_name,
            self.region_name,
        )
        self.assertEqual(request.url, expected_url)

    def test_outpost_endpoint_preserves_key_in_path(self):
        request = self.get_s3_outpost_request(key=self.key)
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.%s.s3-outposts.%s.amazonaws.com/%s' % (
            self.accesspoint_name, self.account, self.outpost_name,
            self.region_name, self.key
        )
        self.assertEqual(request.url, expected_url)

    def test_accesspoint_endpoint(self):
        request = self.get_s3_accesspoint_request()
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.s3-accesspoint.%s.amazonaws.com/' % (
            self.accesspoint_name, self.account, self.region_name
        )
        self.assertEqual(request.url, expected_url)

    def test_accesspoint_preserves_key_in_path(self):
        request = self.get_s3_accesspoint_request(key=self.key)
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.s3-accesspoint.%s.amazonaws.com/%s' % (
            self.accesspoint_name, self.account, self.region_name,
            self.key
        )
        self.assertEqual(request.url, expected_url)

    def test_accesspoint_preserves_scheme(self):
        request = self.get_s3_accesspoint_request(scheme='http://')
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'http://%s-%s.s3-accesspoint.%s.amazonaws.com/' % (
            self.accesspoint_name, self.account, self.region_name,
        )
        self.assertEqual(request.url, expected_url)

    def test_accesspoint_preserves_query_string(self):
        request = self.get_s3_accesspoint_request(querystring='acl')
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.s3-accesspoint.%s.amazonaws.com/?acl' % (
            self.accesspoint_name, self.account, self.region_name,
        )
        self.assertEqual(request.url, expected_url)

    def test_uses_resolved_dns_suffix(self):
        self.endpoint_resolver.construct_endpoint.return_value = {
            'dnsSuffix': 'mysuffix.com'
        }
        request = self.get_s3_accesspoint_request()
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.s3-accesspoint.%s.mysuffix.com/' % (
            self.accesspoint_name, self.account, self.region_name,
        )
        self.assertEqual(request.url, expected_url)

    def test_uses_region_of_client_if_use_arn_disabled(self):
        client_region = 'client-region'
        self.endpoint_setter = self.get_endpoint_setter(
            region=client_region, s3_config={'use_arn_region': False})
        request = self.get_s3_accesspoint_request()
        self.call_set_endpoint(self.endpoint_setter, request=request)
        expected_url = 'https://%s-%s.s3-accesspoint.%s.amazonaws.com/' % (
            self.accesspoint_name, self.account, client_region,
        )
        self.assertEqual(request.url, expected_url)

    def test_accesspoint_supports_custom_endpoint(self):
        endpoint_setter = self.get_endpoint_setter(
            endpoint_url='https://custom.com')
        request = self.get_s3_accesspoint_request()
        self.call_set_endpoint(endpoint_setter, request=request)
        expected_url = 'https://%s-%s.custom.com/' % (
            self.accesspoint_name, self.account,
        )
        self.assertEqual(request.url, expected_url)

    def test_errors_for_mismatching_partition(self):
        endpoint_setter = self.get_endpoint_setter(partition='aws-cn')
        accesspoint_context = self.get_s3_accesspoint_context(partition='aws')
        request = self.get_s3_accesspoint_request(
            accesspoint_context=accesspoint_context)
        with self.assertRaises(UnsupportedS3AccesspointConfigurationError):
            self.call_set_endpoint(endpoint_setter, request=request)

    def test_errors_for_mismatching_partition_when_using_client_region(self):
        endpoint_setter = self.get_endpoint_setter(
            s3_config={'use_arn_region': False}, partition='aws-cn'
        )
        accesspoint_context = self.get_s3_accesspoint_context(partition='aws')
        request = self.get_s3_accesspoint_request(
            accesspoint_context=accesspoint_context)
        with self.assertRaises(UnsupportedS3AccesspointConfigurationError):
            self.call_set_endpoint(endpoint_setter, request=request)

    def test_set_endpoint_for_auto(self):
        endpoint_setter = self.get_endpoint_setter(
            s3_config={'addressing_style': 'auto'})
        request = self.get_s3_request(self.bucket, self.key)
        self.call_set_endpoint(endpoint_setter, request)
        expected_url = 'https://%s.s3.us-west-2.amazonaws.com/%s' % (
            self.bucket, self.key
        )
        self.assertEqual(request.url, expected_url)

    def test_set_endpoint_for_virtual(self):
        endpoint_setter = self.get_endpoint_setter(
            s3_config={'addressing_style': 'virtual'})
        request = self.get_s3_request(self.bucket, self.key)
        self.call_set_endpoint(endpoint_setter, request)
        expected_url = 'https://%s.s3.us-west-2.amazonaws.com/%s' % (
            self.bucket, self.key
        )
        self.assertEqual(request.url, expected_url)

    def test_set_endpoint_for_path(self):
        endpoint_setter = self.get_endpoint_setter(
            s3_config={'addressing_style': 'path'})
        request = self.get_s3_request(self.bucket, self.key)
        self.call_set_endpoint(endpoint_setter, request)
        expected_url = 'https://s3.us-west-2.amazonaws.com/%s/%s' % (
            self.bucket, self.key
        )
        self.assertEqual(request.url, expected_url)

    def test_set_endpoint_for_accelerate(self):
        endpoint_setter = self.get_endpoint_setter(
            s3_config={'use_accelerate_endpoint': True})
        request = self.get_s3_request(self.bucket, self.key)
        self.call_set_endpoint(endpoint_setter, request)
        expected_url = 'https://%s.s3-accelerate.amazonaws.com/%s' % (
            self.bucket, self.key
        )
        self.assertEqual(request.url, expected_url)


class TestContainerMetadataFetcher(unittest.TestCase):
    def setUp(self):
        self.responses = []
        self.http = mock.Mock()
        self.sleep = mock.Mock()

    def create_fetcher(self):
        return ContainerMetadataFetcher(self.http, sleep=self.sleep)

    def fake_response(self, status_code, body):
        response = mock.Mock()
        response.status_code = status_code
        response.content = body
        return response

    def set_http_responses_to(self, *responses):
        http_responses = []
        for response in responses:
            if isinstance(response, Exception):
                # Simulating an error condition.
                http_response = response
            elif hasattr(response, 'status_code'):
                # It's a precreated fake_response.
                http_response = response
            else:
                http_response = self.fake_response(
                    status_code=200, body=json.dumps(response).encode('utf-8'))
            http_responses.append(http_response)
        self.http.send.side_effect = http_responses

    def assert_request(self, method, url, headers):
        request = self.http.send.call_args[0][0]
        self.assertEqual(request.method, method)
        self.assertEqual(request.url, url)
        self.assertEqual(request.headers, headers)

    def assert_can_retrieve_metadata_from(self, full_uri):
        response_body = {'foo': 'bar'}
        self.set_http_responses_to(response_body)
        fetcher = self.create_fetcher()
        response = fetcher.retrieve_full_uri(full_uri)
        self.assertEqual(response, response_body)
        self.assert_request('GET', full_uri, {'Accept': 'application/json'})

    def assert_host_is_not_allowed(self, full_uri):
        response_body = {'foo': 'bar'}
        self.set_http_responses_to(response_body)
        fetcher = self.create_fetcher()
        with self.assertRaisesRegex(ValueError, 'Unsupported host'):
            fetcher.retrieve_full_uri(full_uri)
        self.assertFalse(self.http.send.called)

    def test_can_specify_extra_headers_are_merged(self):
        headers = {
            # The 'Accept' header will override the
            # default Accept header of application/json.
            'Accept': 'application/not-json',
            'X-Other-Header': 'foo',
        }
        self.set_http_responses_to({'foo': 'bar'})
        fetcher = self.create_fetcher()
        response = fetcher.retrieve_full_uri(
            'http://localhost', headers)
        self.assert_request('GET', 'http://localhost', headers)

    def test_can_retrieve_uri(self):
        json_body =  {
            "AccessKeyId" : "a",
            "SecretAccessKey" : "b",
            "Token" : "c",
            "Expiration" : "d"
        }
        self.set_http_responses_to(json_body)

        fetcher = self.create_fetcher()
        response = fetcher.retrieve_uri('/foo?id=1')

        self.assertEqual(response, json_body)
        # Ensure we made calls to the right endpoint.
        headers = {'Accept': 'application/json'}
        self.assert_request('GET', 'http://169.254.170.2/foo?id=1', headers)

    def test_can_retry_requests(self):
        success_response = {
            "AccessKeyId" : "a",
            "SecretAccessKey" : "b",
            "Token" : "c",
            "Expiration" : "d"
        }
        self.set_http_responses_to(
            # First response is a connection error, should
            # be retried.
            ConnectionClosedError(endpoint_url=''),
            # Second response is the successful JSON response
            # with credentials.
            success_response,
        )
        fetcher = self.create_fetcher()
        response = fetcher.retrieve_uri('/foo?id=1')
        self.assertEqual(response, success_response)

    def test_propagates_credential_error_on_http_errors(self):
        self.set_http_responses_to(
            # In this scenario, we never get a successful response.
            ConnectionClosedError(endpoint_url=''),
            ConnectionClosedError(endpoint_url=''),
            ConnectionClosedError(endpoint_url=''),
            ConnectionClosedError(endpoint_url=''),
            ConnectionClosedError(endpoint_url=''),
        )
        # As a result, we expect an appropriate error to be raised.
        fetcher = self.create_fetcher()
        with self.assertRaises(MetadataRetrievalError):
            fetcher.retrieve_uri('/foo?id=1')
        self.assertEqual(self.http.send.call_count, fetcher.RETRY_ATTEMPTS)

    def test_error_raised_on_non_200_response(self):
        self.set_http_responses_to(
            self.fake_response(status_code=404, body=b'Error not found'),
            self.fake_response(status_code=404, body=b'Error not found'),
            self.fake_response(status_code=404, body=b'Error not found'),
        )
        fetcher = self.create_fetcher()
        with self.assertRaises(MetadataRetrievalError):
            fetcher.retrieve_uri('/foo?id=1')
        # Should have tried up to RETRY_ATTEMPTS.
        self.assertEqual(self.http.send.call_count, fetcher.RETRY_ATTEMPTS)

    def test_error_raised_on_no_json_response(self):
        # If the service returns a sucess response but with a body that
        # does not contain JSON, we should still retry up to RETRY_ATTEMPTS,
        # but after exhausting retries we propagate the exception.
        self.set_http_responses_to(
            self.fake_response(status_code=200, body=b'Not JSON'),
            self.fake_response(status_code=200, body=b'Not JSON'),
            self.fake_response(status_code=200, body=b'Not JSON'),
        )
        fetcher = self.create_fetcher()
        with self.assertRaises(MetadataRetrievalError) as e:
            fetcher.retrieve_uri('/foo?id=1')
        self.assertNotIn('Not JSON', str(e.exception))
        # Should have tried up to RETRY_ATTEMPTS.
        self.assertEqual(self.http.send.call_count, fetcher.RETRY_ATTEMPTS)

    def test_can_retrieve_full_uri_with_fixed_ip(self):
        self.assert_can_retrieve_metadata_from(
            'http://%s/foo?id=1' % ContainerMetadataFetcher.IP_ADDRESS)

    def test_localhost_http_is_allowed(self):
        self.assert_can_retrieve_metadata_from('http://localhost/foo')

    def test_localhost_with_port_http_is_allowed(self):
        self.assert_can_retrieve_metadata_from('http://localhost:8000/foo')

    def test_localhost_https_is_allowed(self):
        self.assert_can_retrieve_metadata_from('https://localhost/foo')

    def test_can_use_127_ip_addr(self):
        self.assert_can_retrieve_metadata_from('https://127.0.0.1/foo')

    def test_can_use_127_ip_addr_with_port(self):
        self.assert_can_retrieve_metadata_from('https://127.0.0.1:8080/foo')

    def test_link_local_http_is_not_allowed(self):
        self.assert_host_is_not_allowed('http://169.254.0.1/foo')

    def test_link_local_https_is_not_allowed(self):
        self.assert_host_is_not_allowed('https://169.254.0.1/foo')

    def test_non_link_local_nonallowed_url(self):
        self.assert_host_is_not_allowed('http://169.1.2.3/foo')

    def test_error_raised_on_nonallowed_url(self):
        self.assert_host_is_not_allowed('http://somewhere.com/foo')

    def test_external_host_not_allowed_if_https(self):
        self.assert_host_is_not_allowed('https://somewhere.com/foo')


class TestUnsigned(unittest.TestCase):
    def test_copy_returns_same_object(self):
        self.assertIs(botocore.UNSIGNED, copy.copy(botocore.UNSIGNED))

    def test_deepcopy_returns_same_object(self):
        self.assertIs(botocore.UNSIGNED, copy.deepcopy(botocore.UNSIGNED))


class TestInstanceMetadataFetcher(unittest.TestCase):
    def setUp(self):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._imds_responses = []
        self._send.side_effect = self.get_imds_response
        self._role_name = 'role-name'
        self._creds = {
            'AccessKeyId': 'spam',
            'SecretAccessKey': 'eggs',
            'Token': 'spam-token',
            'Expiration': 'something',
        }
        self._expected_creds = {
            'access_key': self._creds['AccessKeyId'],
            'secret_key': self._creds['SecretAccessKey'],
            'token': self._creds['Token'],
            'expiry_time': self._creds['Expiration'],
            'role_name': self._role_name
        }

    def tearDown(self):
        self._urllib3_patch.stop()

    def add_imds_response(self, body, status_code=200):
        response = botocore.awsrequest.AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers={},
            raw=RawResponse(body)
        )
        self._imds_responses.append(response)

    def add_get_role_name_imds_response(self, role_name=None):
        if role_name is None:
            role_name = self._role_name
        self.add_imds_response(body=role_name.encode('utf-8'))

    def add_get_credentials_imds_response(self, creds=None):
        if creds is None:
            creds = self._creds
        self.add_imds_response(body=json.dumps(creds).encode('utf-8'))

    def add_get_token_imds_response(self, token, status_code=200):
        self.add_imds_response(body=token.encode('utf-8'),
                               status_code=status_code)

    def add_metadata_token_not_supported_response(self):
        self.add_imds_response(b'', status_code=404)

    def add_imds_connection_error(self, exception):
        self._imds_responses.append(exception)

    def add_default_imds_responses(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

    def get_imds_response(self, request):
        response = self._imds_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def _test_imds_base_url(self, config, expected_url):
        self.add_default_imds_responses()

        fetcher = InstanceMetadataFetcher(config=config)
        result = fetcher.retrieve_iam_role_credentials()

        self.assertEqual(result, self._expected_creds)
        self.assertEqual(fetcher.get_base_url(), expected_url)

    def test_disabled_by_environment(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'true'}
        fetcher = InstanceMetadataFetcher(env=env)
        result = fetcher.retrieve_iam_role_credentials()
        self.assertEqual(result, {})
        self._send.assert_not_called()

    def test_disabled_by_environment_mixed_case(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'tRuE'}
        fetcher = InstanceMetadataFetcher(env=env)
        result = fetcher.retrieve_iam_role_credentials()
        self.assertEqual(result, {})
        self._send.assert_not_called()

    def test_disabling_env_var_not_true(self):
        url = 'https://example.com/'
        env = {'AWS_EC2_METADATA_DISABLED': 'false'}

        self.add_default_imds_responses()

        fetcher = InstanceMetadataFetcher(base_url=url, env=env)
        result = fetcher.retrieve_iam_role_credentials()

        self.assertEqual(result, self._expected_creds)

    def test_ec2_metadata_endpoint_service_mode(self):
        configs = [({'ec2_metadata_service_endpoint_mode': 'ipv6'},
                    'http://[fd00:ec2::254]/'),
                ({'ec2_metadata_service_endpoint_mode': 'ipv6'},
                 'http://[fd00:ec2::254]/'),
                ({'ec2_metadata_service_endpoint_mode': 'ipv4'},
                 'http://169.254.169.254/'),
                ({'ec2_metadata_service_endpoint_mode': 'foo'},
                 'http://169.254.169.254/'),
                ({'ec2_metadata_service_endpoint_mode': 'ipv6',
                'ec2_metadata_service_endpoint': 'http://[fd00:ec2::010]/'},
                'http://[fd00:ec2::010]/')]

        for config, expected_url in configs:
            self._test_imds_base_url(config, expected_url)

    def test_metadata_endpoint(self):
        urls = ['http://fd00:ec2:0000:0000:0000:0000:0000:0000/',
                'http://[fd00:ec2::010]/', 'http://192.168.1.1/']
        for url in urls:
            self.assertTrue(is_valid_uri(url))

    def test_ipv6_endpoint_no_brackets_env_var_set(self):
        url = 'http://fd00:ec2::010/'
        config = {'ec2_metadata_service_endpoint': url}
        self.assertFalse(is_valid_ipv6_endpoint_url(url))

    def test_ipv6_invalid_endpoint(self):
        url = 'not.a:valid:dom@in'
        config = {'ec2_metadata_service_endpoint': url}
        with self.assertRaises(InvalidIMDSEndpointError):
            InstanceMetadataFetcher(config=config)

    def test_ipv6_endpoint_env_var_set_and_args(self):
        url = 'http://[fd00:ec2::254]/'
        url_arg = 'http://fd00:ec2:0000:0000:0000:8a2e:0370:7334/'
        config = {'ec2_metadata_service_endpoint': url}

        self.add_default_imds_responses()

        fetcher = InstanceMetadataFetcher(config=config, base_url=url_arg)
        result = fetcher.retrieve_iam_role_credentials()

        self.assertEqual(result, self._expected_creds)
        self.assertEqual(fetcher.get_base_url(), url_arg)

    def test_ipv6_imds_not_allocated(self):
        url = 'http://fd00:ec2:0000:0000:0000:0000:0000:0000/'
        config = {'ec2_metadata_service_endpoint': url}

        self.add_imds_response(
            status_code=400, body=b'{}')

        fetcher = InstanceMetadataFetcher(config=config)
        result = fetcher.retrieve_iam_role_credentials()
        self.assertEqual(result, {})

    def test_ipv6_imds_empty_config(self):
        configs = [({'ec2_metadata_service_endpoint': ''},'http://169.254.169.254/'),
                ({'ec2_metadata_service_endpoint_mode': ''}, 'http://169.254.169.254/'),
                ({}, 'http://169.254.169.254/'),
                (None, 'http://169.254.169.254/')]

        for config, expected_url in configs:
            self._test_imds_base_url(config, expected_url)

    def test_includes_user_agent_header(self):
        user_agent = 'my-user-agent'
        self.add_default_imds_responses()

        InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        self.assertEqual(self._send.call_count, 3)
        for call in self._send.calls:
            self.assertTrue(call[0][0].headers['User-Agent'], user_agent)

    def test_non_200_response_for_role_name_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_get_token_imds_response(token='token')
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_http_connection_error_for_role_name_is_retried(self):
        # Connection related errors should be retried
        self.add_get_token_imds_response(token='token')
        self.add_imds_connection_error(ConnectionClosedError(endpoint_url=''))
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_empty_response_for_role_name_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_get_token_imds_response(token='token')
        self.add_imds_response(body=b'')
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_non_200_response_is_retried(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        # Response for creds that has a 200 status code but has an empty
        # body should be retried.
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_http_connection_errors_is_retried(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        # Connection related errors should be retried
        self.add_imds_connection_error(ConnectionClosedError(endpoint_url=''))
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_empty_response_is_retried(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        # Response for creds that has a 200 status code but is empty.
        # This should be retried.
        self.add_imds_response(body=b'')
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_invalid_json_is_retried(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        # Response for creds that has a 200 status code but is invalid JSON.
        # This should be retried.
        self.add_imds_response(body=b'{"AccessKey":')
        self.add_get_credentials_imds_response()
        result = InstanceMetadataFetcher(
            num_attempts=2).retrieve_iam_role_credentials()
        self.assertEqual(result, self._expected_creds)

    def test_exhaust_retries_on_role_name_request(self):
        self.add_get_token_imds_response(token='token')
        self.add_imds_response(status_code=400, body=b'')
        result = InstanceMetadataFetcher(
            num_attempts=1).retrieve_iam_role_credentials()
        self.assertEqual(result, {})

    def test_exhaust_retries_on_credentials_request(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        self.add_imds_response(status_code=400, body=b'')
        result = InstanceMetadataFetcher(
            num_attempts=1).retrieve_iam_role_credentials()
        self.assertEqual(result, {})

    def test_missing_fields_in_credentials_response(self):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        # Response for creds that has a 200 status code and a JSON body
        # representing an error. We do not necessarily want to retry this.
        self.add_imds_response(
            body=b'{"Code":"AssumeRoleUnauthorizedAccess","Message":"error"}')
        result = InstanceMetadataFetcher().retrieve_iam_role_credentials()
        self.assertEqual(result, {})

    def test_token_is_included(self):
        user_agent = 'my-user-agent'
        self.add_default_imds_responses()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        # Check that subsequent calls after getting the token include the token.
        self.assertEqual(self._send.call_count, 3)
        for call in self._send.call_args_list[1:]:
            self.assertEqual(call[0][0].headers['x-aws-ec2-metadata-token'], 'token')
        self.assertEqual(result, self._expected_creds)

    def test_metadata_token_not_supported_404(self):
        user_agent = 'my-user-agent'
        self.add_imds_response(b'', status_code=404)
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        for call in self._send.call_args_list[1:]:
            self.assertNotIn('x-aws-ec2-metadata-token', call[0][0].headers)
        self.assertEqual(result, self._expected_creds)

    def test_metadata_token_not_supported_403(self):
        user_agent = 'my-user-agent'
        self.add_imds_response(b'', status_code=403)
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        for call in self._send.call_args_list[1:]:
            self.assertNotIn('x-aws-ec2-metadata-token', call[0][0].headers)
        self.assertEqual(result, self._expected_creds)

    def test_metadata_token_not_supported_405(self):
        user_agent = 'my-user-agent'
        self.add_imds_response(b'', status_code=405)
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        for call in self._send.call_args_list[1:]:
            self.assertNotIn('x-aws-ec2-metadata-token', call[0][0].headers)
        self.assertEqual(result, self._expected_creds)

    def test_metadata_token_not_supported_timeout(self):
        user_agent = 'my-user-agent'
        self.add_imds_connection_error(ReadTimeoutError(endpoint_url='url'))
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        for call in self._send.call_args_list[1:]:
            self.assertNotIn('x-aws-ec2-metadata-token', call[0][0].headers)
        self.assertEqual(result, self._expected_creds)

    def test_token_not_supported_exhaust_retries(self):
        user_agent = 'my-user-agent'
        self.add_imds_connection_error(ConnectTimeoutError(endpoint_url='url'))
        self.add_get_role_name_imds_response()
        self.add_get_credentials_imds_response()

        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()

        for call in self._send.call_args_list[1:]:
            self.assertNotIn('x-aws-ec2-metadata-token', call[0][0].headers)
        self.assertEqual(result, self._expected_creds)

    def test_metadata_token_bad_request_yields_no_credentials(self):
        user_agent = 'my-user-agent'
        self.add_imds_response(b'', status_code=400)
        result = InstanceMetadataFetcher(
            user_agent=user_agent).retrieve_iam_role_credentials()
        self.assertEqual(result, {})

    def _get_datetime(
       self, dt=None, offset=None, offset_func=operator.add
    ):
        if dt is None:
            dt = datetime.datetime.utcnow()
        if offset is not None:
            dt = offset_func(dt, offset)

        return dt

    def _get_default_creds(self, overrides=None):
        if overrides is None:
            overrides = {}

        creds = {
            'AccessKeyId': 'access',
            'SecretAccessKey': 'secret',
            'Token': 'token',
            'Expiration': '1970-01-01T00:00:00'
        }
        creds.update(overrides)
        return creds

    def _convert_creds_to_imds_fetcher(self, creds):
        return {
            'access_key': creds['AccessKeyId'],
            'secret_key': creds['SecretAccessKey'],
            'token': creds['Token'],
            'expiry_time': creds['Expiration'],
            'role_name': self._role_name
        }

    def _add_default_imds_response(self, status_code=200, creds=''):
        self.add_get_token_imds_response(token='token')
        self.add_get_role_name_imds_response()
        self.add_imds_response(
            status_code=200,
            body=json.dumps(creds).encode('utf-8')
        )

    def mock_randint(self, int_val=600):
        randint_mock = mock.Mock()
        randint_mock.return_value = int_val
        return randint_mock

    @FreezeTime(module=botocore.utils.datetime, date=DATE)
    def test_expiry_time_extension(self):
        current_time = self._get_datetime()
        expiration_time = self._get_datetime(
            dt=current_time, offset=datetime.timedelta(seconds=14*60)
        )
        new_expiration = self._get_datetime(
            dt=current_time, offset=datetime.timedelta(seconds=20*60)
        )

        creds = self._get_default_creds(
            {"Expiration": expiration_time.strftime(DT_FORMAT)}
        )
        expected_data = self._convert_creds_to_imds_fetcher(creds)
        expected_data["expiry_time"] = new_expiration.strftime(DT_FORMAT)

        self._add_default_imds_response(200, creds)

        with mock.patch("random.randint", self.mock_randint()):
            fetcher = InstanceMetadataFetcher()
            result = fetcher.retrieve_iam_role_credentials()
            assert result == expected_data

    @FreezeTime(module=botocore.utils.datetime, date=DATE)
    def test_expired_expiry_extension(self):
        current_time = self._get_datetime()
        expiration_time = self._get_datetime(
            dt=current_time,
            offset=datetime.timedelta(seconds=14*60),
            offset_func=operator.sub
        )
        new_expiration = self._get_datetime(
            dt=current_time, offset=datetime.timedelta(seconds=20*60)
        )
        assert current_time > expiration_time
        assert new_expiration > current_time

        creds = self._get_default_creds(
            {"Expiration": expiration_time.strftime(DT_FORMAT)}
        )
        expected_data = self._convert_creds_to_imds_fetcher(creds)
        expected_data["expiry_time"] = new_expiration.strftime(DT_FORMAT)

        self._add_default_imds_response(200, creds)

        with mock.patch("random.randint", self.mock_randint()):
            fetcher = InstanceMetadataFetcher()
            result = fetcher.retrieve_iam_role_credentials()
            assert result == expected_data

    @FreezeTime(module=botocore.utils.datetime, date=DATE)
    def test_expiry_extension_with_config(self):
        current_time = self._get_datetime()
        expiration_time = self._get_datetime(
            dt=current_time,
            offset=datetime.timedelta(seconds=14*60),
            offset_func=operator.sub
        )
        new_expiration = self._get_datetime(
            dt=current_time, offset=datetime.timedelta(seconds=25*60)
        )
        assert current_time > expiration_time
        assert new_expiration > current_time

        creds = self._get_default_creds(
            {"Expiration": expiration_time.strftime(DT_FORMAT)}
        )
        expected_data = self._convert_creds_to_imds_fetcher(creds)
        expected_data["expiry_time"] = new_expiration.strftime(DT_FORMAT)

        self._add_default_imds_response(200, creds)

        with mock.patch("random.randint", self.mock_randint()):
            fetcher = InstanceMetadataFetcher(
                config={"ec2_credential_refresh_window": 15*60}
            )
            result = fetcher.retrieve_iam_role_credentials()
            assert result == expected_data

    @FreezeTime(module=botocore.utils.datetime, date=DATE)
    def test_expiry_extension_with_bad_datetime(self):
        bad_datetime = "May 20th, 2020 19:00:00"
        creds = self._get_default_creds(
            {"Expiration": bad_datetime}
        )
        self._add_default_imds_response(200, creds)

        fetcher = InstanceMetadataFetcher(
            config={"ec2_credential_refresh_window": 15*60}
        )
        results = fetcher.retrieve_iam_role_credentials()
        assert results['expiry_time'] == bad_datetime


class TestSSOTokenFetcher(unittest.TestCase):
    def setUp(self):
        super(TestSSOTokenFetcher, self).setUp()
        self.cache = {}
        self.start_url = 'https://d-abc123.awsapps.com/start'
        self.sso_region = 'us-west-2'
        # The token cache key is the sha1 of the start url
        self.token_cache_key = '40a89917e3175433e361b710a9d43528d7f1890a'
        self.client_id_key = 'd75f79f67bab3f92a2b1450471c0c2574de0dca4'
        # This is just an arbitrary point in time that we can pin to
        self.now = datetime.datetime(2008, 9, 23, 12, 26, 40, tzinfo=tzutc())
        self.now_timestamp = 1222172800
        self.mock_time_fetcher = mock.Mock(return_value=self.now)
        self.mock_sleep = mock.Mock()
        self.sso_oidc = Session().create_client(
            'sso-oidc',
            region_name='us-west-2',
        )
        self.stubber = Stubber(self.sso_oidc)
        self.mock_session = mock.Mock(spec=Session)
        self.mock_session.create_client.return_value = self.sso_oidc
        self.sso_token_fetcher = SSOTokenFetcher(
            self.sso_region,
            client_creator=self.mock_session.create_client,
            cache=self.cache,
            time_fetcher=self.mock_time_fetcher,
            sleep=self.mock_sleep,
        )

        self.register_expected_params = {
            'clientName': 'botocore-client-1222172800',
            'clientType': 'public',
        }
        self.register_response = {
            'clientSecretExpiresAt': self.now_timestamp + 1000,
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
        }

        self.authorization_expected_params = {
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
            'startUrl': 'https://d-abc123.awsapps.com/start',
        }
        self.authorization_response = {
            'interval': 1,
            'expiresIn': 600,
            'userCode': 'foo',
            'deviceCode': 'foo-device-code',
            'verificationUri': 'https://sso.fake/device',
            'verificationUriComplete': 'https://sso.fake/device?user_code=foo',
        }

        self.token_expected_params = {
            'grantType': 'urn:ietf:params:oauth:grant-type:device_code',
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
            'deviceCode': 'foo-device-code',
        }
        self.token_response = {
            'expiresIn': 28800,
            'tokenType': 'Bearer',
            'accessToken': 'foo.token.string',
        }

    def _expires_at(self, seconds):
        return self.now + datetime.timedelta(seconds=seconds)

    def _add_register_client_response(self):
        self.stubber.add_response(
            'register_client',
            self.register_response,
            self.register_expected_params,
        )

    def _add_start_device_authorization_response(self):
        self.stubber.add_response(
            'start_device_authorization',
            self.authorization_response,
            self.authorization_expected_params,
        )

    def _add_create_token_responses(self):
        # In the standard flow we'll try to create the token once in the
        # case it's already been pre-authorized. Raise at least one pending
        # exception to simulate this.
        self.stubber.add_client_error(
            'create_token',
            service_error_code='AuthorizationPendingException',
            expected_params=self.token_expected_params,
        )
        self.stubber.add_response(
            'create_token',
            self.token_response,
            self.token_expected_params,
        )

    def _add_basic_device_auth_flow_responses(self):
        self._add_register_client_response()
        self._add_start_device_authorization_response()
        self._add_create_token_responses()

    def test_basic_fetch_token(self):
        self._add_basic_device_auth_flow_responses()

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

    def test_fetch_token_writes_cache(self):
        self._add_basic_device_auth_flow_responses()

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

        expected_client_id = {
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
            'expiresAt': self._expires_at(1000),
        }
        self.assertEqual(self.cache[self.client_id_key], expected_client_id)

        expected_token = {
            'region': self.sso_region,
            'startUrl': self.start_url,
            'accessToken': 'foo.token.string',
            'expiresAt': self._expires_at(28800),
            'clientId': expected_client_id['clientId'],
            'clientSecret': expected_client_id['clientSecret'],
            'registrationExpiresAt': expected_client_id['expiresAt'],
        }
        self.assertEqual(self.cache[self.token_cache_key], expected_token)

    def test_fetch_token_respects_cached_client_id(self):
        expected_client_id = {
            'clientId': 'bar-client-id',
            'clientSecret': 'bar-client-secret',
            'expiresAt': self._expires_at(1000),
        }
        self.cache[self.client_id_key] = expected_client_id

        self.authorization_expected_params.update(
            clientId='bar-client-id',
            clientSecret='bar-client-secret',
        )
        self._add_start_device_authorization_response()
        self.token_expected_params.update(
            clientId='bar-client-id',
            clientSecret='bar-client-secret',
        )
        self._add_create_token_responses()

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

        # Ensure the cached client-id hasn't changed
        self.assertEqual(self.cache[self.client_id_key], expected_client_id)

    def test_fetch_token_respects_cached_token(self):
        expected_token = {
            'region': self.sso_region,
            'startUrl': self.start_url,
            'accessToken': 'bar.token.string',
            'expiresAt': self._expires_at(28800),
        }
        self.cache[self.token_cache_key] = expected_token

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'bar.token.string')
        self.stubber.assert_no_pending_responses()

        # Ensure the cached token hasn't changed
        self.assertEqual(self.cache[self.token_cache_key], expected_token)

    def test_fetch_token_expired_cache(self):
        expired_client_id = {
            'clientId': 'bar-client-id',
            'clientSecret': 'bar-client-secret',
            'expiresAt': self._expires_at(-1),
        }
        self.cache[self.client_id_key] = expired_client_id
        expired_token = {
            'accessToken': 'bar.token.string',
            'expiresAt': self._expires_at(-1),
        }
        self.cache[self.token_cache_key] = expired_token

        self._add_basic_device_auth_flow_responses()
        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

        # Ensure the expired cache items were replaced
        expected_client_id = {
            'clientId': 'foo-client-id',
            'clientSecret': 'foo-client-secret',
            'expiresAt': self._expires_at(1000),
        }
        self.assertEqual(self.cache[self.client_id_key], expected_client_id)
        expected_token = {
            'region': self.sso_region,
            'startUrl': self.start_url,
            'accessToken': 'foo.token.string',
            'expiresAt': self._expires_at(28800),
            'clientId': expected_client_id['clientId'],
            'clientSecret': expected_client_id['clientSecret'],
            'registrationExpiresAt': expected_client_id['expiresAt'],
        }
        self.assertEqual(self.cache[self.token_cache_key], expected_token)

    def test_fetch_token_respects_authorization_pending(self):
        self._add_register_client_response()
        self._add_start_device_authorization_response()
        self.stubber.add_client_error(
            'create_token',
            service_error_code='AuthorizationPendingException',
            expected_params=self.token_expected_params,
        )
        self._add_create_token_responses()

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

    def test_fetch_token_respects_slow_down(self):
        self._add_register_client_response()
        self._add_start_device_authorization_response()
        self.stubber.add_client_error(
            'create_token',
            service_error_code='SlowDownException',
            expected_params=self.token_expected_params,
        )
        self._add_create_token_responses()

        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()
        # We should have slept for longer due to the slow down exception
        # The base delay is 1, plus 5 for the slow down exception
        self.mock_sleep.assert_called_with(6)

    def test_fetch_token_default_interval(self):
        del self.authorization_response['interval']
        self._add_register_client_response()
        self._add_start_device_authorization_response()
        self.stubber.add_client_error(
            'create_token',
            service_error_code='AuthorizationPendingException',
            expected_params=self.token_expected_params,
        )
        self._add_create_token_responses()
        with self.stubber:
            token = self.sso_token_fetcher.fetch_token(self.start_url)
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()
        self.mock_sleep.assert_called_with(5)

    def test_fetch_token_force_refresh(self):
        expected_token = {
            'region': self.sso_region,
            'startUrl': self.start_url,
            'accessToken': 'bar.token.string',
            'expiresAt': self._expires_at(28800),
        }
        self.cache[self.token_cache_key] = expected_token

        self._add_basic_device_auth_flow_responses()
        with self.stubber:
            fetcher = self.sso_token_fetcher
            token = fetcher.fetch_token(self.start_url, force_refresh=True)
        # Ensure we get a new token even though the old one was still valid
        self.assertEqual(token.get('accessToken'), 'foo.token.string')
        self.stubber.assert_no_pending_responses()

    def test_on_pending_authorization_callback_called(self):
        handler = mock.Mock()
        self.sso_token_fetcher = SSOTokenFetcher(
            self.sso_region,
            client_creator=self.mock_session.create_client,
            cache=self.cache,
            time_fetcher=self.mock_time_fetcher,
            sleep=self.mock_sleep,
            on_pending_authorization=handler,
        )
        self._add_basic_device_auth_flow_responses()
        with self.stubber:
            self.sso_token_fetcher.fetch_token(self.start_url)
        self.stubber.assert_no_pending_responses()
        handler.assert_called_with(
            interval=1,
            userCode='foo',
            deviceCode='foo-device-code',
            expiresAt=self._expires_at(600),
            verificationUri='https://sso.fake/device',
            verificationUriComplete='https://sso.fake/device?user_code=foo',
        )

    def test_fetch_token_authorization_expires(self):
        self._add_register_client_response()
        self._add_start_device_authorization_response()
        self.stubber.add_client_error(
            'create_token',
            service_error_code='ExpiredTokenException',
            expected_params=self.token_expected_params,
        )
        with self.stubber:
            with self.assertRaises(PendingAuthorizationExpiredError):
                self.sso_token_fetcher.fetch_token(self.start_url)
        self.stubber.assert_no_pending_responses()


class TestSSOTokenLoader(unittest.TestCase):
    def setUp(self):
        super(TestSSOTokenLoader, self).setUp()
        self.session_name = 'admin'
        self.start_url = 'https://d-abc123.awsapps.com/start'
        self.cache_key = '40a89917e3175433e361b710a9d43528d7f1890a'
        self.session_cache_key = 'd033e22ae348aeb5660fc2140aec35850c4da997'
        self.access_token = 'totally.a.token'
        self.cached_token = {
            'accessToken': self.access_token,
            'expiresAt': '2002-10-18T03:52:38UTC'
        }
        self.cache = {}
        self.loader = SSOTokenLoader(cache=self.cache)

    def test_can_load_token_exists(self):
        self.cache[self.cache_key] = self.cached_token
        access_token = self.loader(self.start_url)
        self.assertEqual(self.cached_token, access_token)

    def test_can_handle_does_not_exist(self):
        with self.assertRaises(SSOTokenLoadError):
            access_token = self.loader(self.start_url)

    def test_can_handle_invalid_cache(self):
        self.cache[self.cache_key] = {}
        with self.assertRaises(SSOTokenLoadError):
            access_token = self.loader(self.start_url)

    def test_can_save_token(self):
        self.loader.save_token(self.start_url, self.cached_token)
        access_token = self.loader(self.start_url)
        self.assertEqual(self.cached_token, access_token)

    def test_can_save_token_sso_session(self):
        self.loader.save_token(
            self.start_url,
            self.cached_token,
            session_name=self.session_name,
        )
        access_token = self.loader(
            self.start_url,
            session_name=self.session_name,
        )
        self.assertEqual(self.cached_token, access_token)

    def test_can_load_token_exists_sso_session_name(self):
        self.cache[self.session_cache_key] = self.cached_token
        access_token = self.loader(
            self.start_url,
            session_name=self.session_name,
        )
        self.assertEqual(self.cached_token, access_token)


class TestOriginalLDLibraryPath(unittest.TestCase):
    def test_swaps_original_ld_library_path(self):
        env = {'LD_LIBRARY_PATH_ORIG': '/my/original',
               'LD_LIBRARY_PATH': '/pyinstallers/version'}
        with original_ld_library_path(env):
            self.assertEqual(env['LD_LIBRARY_PATH'],
                             '/my/original')
        self.assertEqual(env['LD_LIBRARY_PATH'],
                            '/pyinstallers/version')

    def test_no_ld_library_path_original(self):
        env = {'LD_LIBRARY_PATH': '/pyinstallers/version'}
        with original_ld_library_path(env):
            self.assertIsNone(env.get('LD_LIBRARY_PATH'))
        self.assertEqual(env['LD_LIBRARY_PATH'],
                            '/pyinstallers/version')

    def test_no_ld_library_path(self):
        env = {'OTHER_VALUE': 'foo'}
        with original_ld_library_path(env):
            self.assertIsNone(env.get('LD_LIBRARY_PATH'))
            self.assertEqual(env, {'OTHER_VALUE': 'foo'})
        self.assertEqual(env, {'OTHER_VALUE': 'foo'})


@pytest.mark.parametrize(
    'header_name, headers, expected',
    (
        ('test_header', {'test_header': 'foo'}, True),
        ('Test_Header', {'test_header': 'foo'}, True),
        ('test_header', {'Test_Header': 'foo'}, True),
        ('missing_header', {'Test_Header': 'foo'}, False),
        (None, {'Test_Header': 'foo'}, False),
        ('test_header', HeadersDict({'test_header': 'foo'}), True),
        ('Test_Header', HeadersDict({'test_header': 'foo'}), True),
        ('test_header', HeadersDict({'Test_Header': 'foo'}), True),
        ('missing_header', HeadersDict({'Test_Header': 'foo'}), False),
        (None, HeadersDict({'Test_Header': 'foo'}), False),
    )
)
def test_has_header(header_name, headers, expected):
    assert has_header(header_name, headers) is expected


class TestDetermineContentLength(unittest.TestCase):
    def test_basic_bytes(self):
        length = determine_content_length(b'hello')
        self.assertEqual(length, 5)

    def test_empty_bytes(self):
        length = determine_content_length(b'')
        self.assertEqual(length, 0)

    def test_buffered_io_base(self):
        length = determine_content_length(io.BufferedIOBase())
        self.assertIsNone(length)

    def test_none(self):
        length = determine_content_length(None)
        self.assertEqual(length, 0)

    def test_basic_len_obj(self):
        class HasLen(object):
            def __len__(self):
                return 12

        length = determine_content_length(HasLen())
        self.assertEqual(length, 12)

    def test_non_seekable_fileobj(self):
        class Readable(object):
            def read(self, *args, **kwargs):
                pass

        length = determine_content_length(Readable())
        self.assertIsNone(length)

    def test_seekable_fileobj(self):
        class Seekable(object):
            _pos = 0

            def read(self, *args, **kwargs):
                pass

            def tell(self, *args, **kwargs):
                return self._pos

            def seek(self, *args, **kwargs):
                self._pos = 50

        length = determine_content_length(Seekable())
        self.assertEqual(length, 50)
