# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from botocore import regions
from botocore.exceptions import EndpointVariantError, NoRegionError
from tests import unittest


class TestEndpointResolver(unittest.TestCase):
    def _template(self):
        return {
            'partitions': [
                {
                    'partition': 'aws',
                    'dnsSuffix': 'amazonaws.com',
                    'regionRegex': r'^(us|eu)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}',
                        'variants': [
                            {
                                'hostname': '{service}-fips.{region}.{dnsSuffix}',
                                'tags': ['fips'],
                            },
                            {
                                'dnsSuffix': 'api.aws',
                                'hostname': '{service}.{region}.{dnsSuffix}',
                                'tags': ['dualstack'],
                            },
                            {
                                'dnsSuffix': 'api.aws',
                                'hostname': '{service}-fips.{region}.{dnsSuffix}',
                                'tags': ['dualstack', 'fips'],
                            },
                        ],
                    },
                    'regions': {
                        'us-foo': {'regionName': 'a'},
                        'us-bar': {'regionName': 'b'},
                        'eu-baz': {'regionName': 'd'},
                    },
                    'services': {
                        'ec2': {
                            'defaults': {
                                'protocols': ['http', 'https'],
                                'variants': [
                                    {
                                        'dnsSuffix': 'api.aws',
                                        'hostname': 'api.ec2.{region}.{dnsSuffix}',
                                        'tags': ['dualstack'],
                                    }
                                ],
                            },
                            'endpoints': {
                                'us-foo': {
                                    'hostname': 'ec2.us-foo.amazonaws.com',
                                    'variants': [
                                        {
                                            'dnsSuffix': 'api.aws',
                                            'hostname': 'ec2.foo.{dnsSuffix}',
                                            'tags': ['dualstack'],
                                        },
                                        {
                                            'hostname': 'ec2-fips.foo.amazonaws.com',
                                            'tags': ['fips'],
                                        },
                                        {
                                            'hostname': 'ec2-fips.foo.api.aws',
                                            'tags': ['fips', 'dualstack'],
                                        },
                                    ],
                                },
                                'us-bar': {},
                                'us-dep': {
                                    'deprecated': True,
                                },
                                'us-fizz': {
                                    'credentialScope': {'region': 'us-fizz'},
                                    'hostname': 'ec2.us-fizz.amazonaws.com',
                                    'variants': [
                                        {
                                            'hostname': 'ec2.fizz.api.aws',
                                            'tags': ['dualstack'],
                                        }
                                    ],
                                },
                                'eu-baz': {},
                                'd': {},
                            },
                        },
                        's3': {
                            'defaults': {
                                'sslCommonName': '{service}.{region}.{dnsSuffix}',
                                'variants': [
                                    {
                                        'hostname': 's3.dualstack.{region}.{dnsSuffix}',
                                        'tags': ['dualstack'],
                                    },
                                    {
                                        'hostname': 's3-fips.{region}.{dnsSuffix}',
                                        'tags': ['fips'],
                                    },
                                    {
                                        'hostname': 's3-fips.dualstack.{region}.{dnsSuffix}',
                                        'tags': ['dualstack', 'fips'],
                                    },
                                ],
                            },
                            'endpoints': {
                                'us-foo': {
                                    'sslCommonName': '{region}.{service}.{dnsSuffix}'
                                },
                                'us-bar': {},
                                'us-fizz': {
                                    'hostname': 's3.api.us-fizz.amazonaws.com',
                                    'variants': [
                                        {'tags': ['dualstack']},
                                        {'tags': ['fips']},
                                    ],
                                },
                                'eu-baz': {'hostname': 'foo'},
                            },
                        },
                        'not-regionalized': {
                            'isRegionalized': False,
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'not-regionalized'},
                                'us-foo': {},
                                'eu-baz': {},
                            },
                        },
                        'non-partition': {
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'host'},
                                'us-foo': {},
                            },
                        },
                        'merge': {
                            'defaults': {
                                'signatureVersions': ['v2'],
                                'protocols': ['http'],
                            },
                            'endpoints': {
                                'us-foo': {'signatureVersions': ['v4']},
                                'us-bar': {'protocols': ['https']},
                            },
                        },
                    },
                },
                {
                    'partition': 'foo',
                    'dnsSuffix': 'foo.com',
                    'regionRegex': r'^(foo)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}',
                        'protocols': ['http'],
                        'foo': 'bar',
                    },
                    'regions': {
                        'foo-1': {'regionName': '1'},
                        'foo-2': {'regionName': '2'},
                        'foo-3': {'regionName': '3'},
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'foo-1': {'foo': 'baz'},
                                'foo-2': {},
                                'foo-3': {},
                            }
                        }
                    },
                },
                {
                    'partition': 'aws-iso',
                    'dnsSuffix': 'amazonaws.com',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}',
                        'protocols': ['http'],
                    },
                    'regions': {
                        'foo-1': {'regionName': '1'},
                        'foo-2': {'regionName': '2'},
                        'foo-3': {'regionName': '3'},
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'foo-1': {'foo': 'baz'},
                                'foo-2': {},
                                'foo-3': {},
                            }
                        }
                    },
                },
            ]
        }

    def test_ensures_region_is_not_none(self):
        with self.assertRaises(NoRegionError):
            resolver = regions.EndpointResolver(self._template())
            resolver.construct_endpoint('foo', None)

    def test_ensures_required_keys_present(self):
        with self.assertRaises(ValueError):
            regions.EndpointResolver({})

    def test_returns_empty_list_when_listing_for_different_partition(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertEqual([], resolver.get_available_endpoints('ec2', 'bar'))

    def test_returns_empty_list_when_no_service_found(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertEqual([], resolver.get_available_endpoints('what?'))

    def test_gets_endpoint_names(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=True
        )
        self.assertEqual(
            ['d', 'eu-baz', 'us-bar', 'us-dep', 'us-fizz', 'us-foo'],
            sorted(result),
        )

    def test_gets_endpoint_names_for_partition(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=True, partition_name='foo'
        )
        self.assertEqual(['foo-1', 'foo-2', 'foo-3'], sorted(result))

    def test_list_regional_endpoints_only(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=False
        )
        self.assertEqual(['eu-baz', 'us-bar', 'us-foo'], sorted(result))

    def test_returns_none_when_no_match(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertIsNone(resolver.construct_endpoint('foo', 'baz'))

    def test_constructs_regionalized_endpoints_for_exact_matches(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized', 'eu-baz')
        self.assertEqual(
            'not-regionalized.eu-baz.amazonaws.com', result['hostname']
        )
        self.assertEqual('aws', result['partition'])
        self.assertEqual('eu-baz', result['endpointName'])

    def test_constructs_partition_endpoints_for_real_partition_region(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized', 'us-bar')
        self.assertEqual('not-regionalized', result['hostname'])
        self.assertEqual('aws', result['partition'])
        self.assertEqual('aws', result['endpointName'])

    def test_constructs_partition_endpoints_for_regex_match(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized', 'us-abc')
        self.assertEqual('not-regionalized', result['hostname'])

    def test_constructs_endpoints_for_regionalized_regex_match(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('s3', 'us-abc')
        self.assertEqual('s3.us-abc.amazonaws.com', result['hostname'])

    def test_constructs_endpoints_for_unknown_service_but_known_region(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('unknown', 'us-foo')
        self.assertEqual('unknown.us-foo.amazonaws.com', result['hostname'])

    def test_merges_service_keys(self):
        resolver = regions.EndpointResolver(self._template())
        us_foo = resolver.construct_endpoint('merge', 'us-foo')
        us_bar = resolver.construct_endpoint('merge', 'us-bar')
        self.assertEqual(['http'], us_foo['protocols'])
        self.assertEqual(['v4'], us_foo['signatureVersions'])
        self.assertEqual(['https'], us_bar['protocols'])
        self.assertEqual(['v2'], us_bar['signatureVersions'])

    def test_merges_partition_default_keys_with_no_overwrite(self):
        resolver = regions.EndpointResolver(self._template())
        resolved = resolver.construct_endpoint('ec2', 'foo-1')
        self.assertEqual('baz', resolved['foo'])
        self.assertEqual(['http'], resolved['protocols'])

    def test_merges_partition_default_keys_with_overwrite(self):
        resolver = regions.EndpointResolver(self._template())
        resolved = resolver.construct_endpoint('ec2', 'foo-2')
        self.assertEqual('bar', resolved['foo'])
        self.assertEqual(['http'], resolved['protocols'])

    def test_gives_hostname_and_common_name_unaltered(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('s3', 'eu-baz')
        self.assertEqual('s3.eu-baz.amazonaws.com', result['sslCommonName'])
        self.assertEqual('foo', result['hostname'])

    def tests_uses_partition_endpoint_when_no_region_provided(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized')
        self.assertEqual('not-regionalized', result['hostname'])
        self.assertEqual('aws', result['endpointName'])

    def test_returns_dns_suffix_if_available(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized')
        self.assertEqual(result['dnsSuffix'], 'amazonaws.com')

    def test_construct_dualstack_from_endpoint_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2', 'us-foo', use_dualstack_endpoint=True
        )
        self.assertEqual(result['hostname'], 'ec2.foo.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_construct_dualstack_endpoint_from_service_default_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2', 'us-bar', use_dualstack_endpoint=True
        )
        self.assertEqual(result['hostname'], 'api.ec2.us-bar.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_construct_dualstack_endpoint_from_partition_default_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'dynamodb', 'us-bar', use_dualstack_endpoint=True
        )
        self.assertEqual(result['hostname'], 'dynamodb.us-bar.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_constructs_dualstack_endpoint_no_hostname_in_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            's3', 'us-fizz', use_dualstack_endpoint=True
        )
        self.assertEqual('s3.dualstack.us-fizz.api.aws', result['hostname'])

    def test_constructs_endpoint_dualstack_no_variant_dns_suffix(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            's3', 'us-bar', use_dualstack_endpoint=True
        )
        self.assertEqual('s3.dualstack.us-bar.api.aws', result['hostname'])

    def test_construct_dualstack_endpoint_iso_partition_raise_exception(self):
        with self.assertRaises(EndpointVariantError):
            resolver = regions.EndpointResolver(self._template())
            resolver.construct_endpoint(
                'foo', 'foo-1', 'aws-iso', use_dualstack_endpoint=True
            )

    def test_get_partition_dns_suffix_no_tags(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertEqual(
            resolver.get_partition_dns_suffix('aws'), 'amazonaws.com'
        )

    def test_get_partition_dualstack_dns_suffix(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertEqual(
            resolver.get_partition_dns_suffix('aws', ['dualstack']), 'api.aws'
        )

    def test_get_partition_dualstack_dns_suffix_does_not_exist(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertIsNone(
            resolver.get_partition_dns_suffix('foo', ['dualstack'])
        )

    def test_get_available_fips_endpoints(self):
        resolver = regions.EndpointResolver(self._template())
        fips_endpoints = resolver.get_available_endpoints(
            'ec2', endpoint_variant_tags=['fips']
        )
        self.assertEqual(fips_endpoints, ['us-foo'])

    def test_get_available_dualstack_endpoints(self):
        resolver = regions.EndpointResolver(self._template())
        dualstack_endpoints = resolver.get_available_endpoints(
            'ec2', endpoint_variant_tags=['dualstack']
        )
        self.assertEqual(dualstack_endpoints, ['us-foo'])

    def test_get_available_fips_and_dualstack_endpoints(self):
        resolver = regions.EndpointResolver(self._template())
        fips_and_dualstack_endpoints = resolver.get_available_endpoints(
            'ec2', endpoint_variant_tags=['fips', 'dualstack']
        )
        self.assertEqual(fips_and_dualstack_endpoints, ['us-foo'])

    def test_get_available_fips_endpoints_none(self):
        resolver = regions.EndpointResolver(self._template())
        fips_endpoints = resolver.get_available_endpoints(
            'ec2', 'foo', endpoint_variant_tags=['fips']
        )
        self.assertEqual(fips_endpoints, [])

    def test_get_available_dualstack_endpoints_none(self):
        resolver = regions.EndpointResolver(self._template())
        dualstack_endpoints = resolver.get_available_endpoints(
            'ec2', 'foo', endpoint_variant_tags=['dualstack']
        )
        self.assertEqual(dualstack_endpoints, [])

    def test_get_available_fips_and_dualstack_endpoints_none(self):
        resolver = regions.EndpointResolver(self._template())
        fips_and_dualstack_endpoints = resolver.get_available_endpoints(
            'ec2', 'foo', endpoint_variant_tags=['fips', 'dualstack']
        )
        self.assertEqual(fips_and_dualstack_endpoints, [])

    def test_construct_deprecated_endpoint_raises_warning(self):
        resolver = regions.EndpointResolver(self._template())
        with self.assertLogs('botocore.regions', level='WARNING') as log:
            result = resolver.construct_endpoint(
                'ec2',
                'us-dep',
                use_fips_endpoint=True,
            )
            self.assertIn('deprecated endpoint', log.output[0])
            self.assertEqual(
                result['hostname'], 'ec2-fips.us-dep.amazonaws.com'
            )
            self.assertEqual(result['dnsSuffix'], 'amazonaws.com')

    def test_construct_fips_from_endpoint_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2', 'us-foo', use_fips_endpoint=True
        )
        self.assertEqual(result['hostname'], 'ec2-fips.foo.amazonaws.com')
        self.assertEqual(result['dnsSuffix'], 'amazonaws.com')

    def test_construct_fips_endpoint_from_service_default_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2', 'us-bar', use_fips_endpoint=True
        )
        self.assertEqual(result['hostname'], 'ec2-fips.us-bar.amazonaws.com')
        self.assertEqual(result['dnsSuffix'], 'amazonaws.com')

    def test_construct_fips_endpoint_from_partition_default_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'dynamodb', 'us-bar', use_fips_endpoint=True
        )
        self.assertEqual(
            result['hostname'], 'dynamodb-fips.us-bar.amazonaws.com'
        )
        self.assertEqual(result['dnsSuffix'], 'amazonaws.com')

    def test_constructs_fips_endpoint_no_hostname_in_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            's3', 'us-fizz', use_fips_endpoint=True
        )
        self.assertEqual('s3-fips.us-fizz.amazonaws.com', result['hostname'])

    def test_construct_dualstack_and_fips_from_endpoint_variant(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2',
            'us-foo',
            use_dualstack_endpoint=True,
            use_fips_endpoint=True,
        )
        self.assertEqual(result['hostname'], 'ec2-fips.foo.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_construct_dualstack_and_fips_endpoint_from_service_default_variant(
        self,
    ):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'ec2',
            'us-bar',
            use_dualstack_endpoint=True,
            use_fips_endpoint=True,
        )
        self.assertEqual(result['hostname'], 'ec2-fips.us-bar.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_construct_dualstack_and_fips_endpoint_from_partition_default_variant(
        self,
    ):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            'dynamodb',
            'us-bar',
            use_dualstack_endpoint=True,
            use_fips_endpoint=True,
        )
        self.assertEqual(result['hostname'], 'dynamodb-fips.us-bar.api.aws')
        self.assertEqual(result['dnsSuffix'], 'api.aws')

    def test_constructs_dualstack_and_fips_endpoint_no_hostname_in_variant(
        self,
    ):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint(
            's3',
            'us-fizz',
            use_dualstack_endpoint=True,
            use_fips_endpoint=True,
        )
        self.assertEqual(
            's3-fips.dualstack.us-fizz.api.aws', result['hostname']
        )

    def test_construct_fips_endpoint_no_variant_raise_exception(self):
        with self.assertRaises(EndpointVariantError):
            resolver = regions.EndpointResolver(self._template())
            resolver.construct_endpoint(
                'ec2', 'foo-1', 'foo', use_fips_endpoint=True
            )

    def test_construct_dualstack_endpoint_no_variant_raise_exception(self):
        with self.assertRaises(EndpointVariantError):
            resolver = regions.EndpointResolver(self._template())
            resolver.construct_endpoint(
                'ec2', 'foo-1', 'foo', use_dualstack_endpoint=True
            )

    def test_construct_dualstack_and_fips_endpoint_no_variant_raise_exception(
        self,
    ):
        with self.assertRaises(EndpointVariantError):
            resolver = regions.EndpointResolver(self._template())
            resolver.construct_endpoint(
                'ec2',
                'foo-1',
                'foo',
                use_dualstack_endpoint=True,
                use_fips_endpoint=True,
            )


def _variant_test_definitions():
    return [
        {
            "service": "default-pattern-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "default-pattern-service.us-west-2.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "default-pattern-service-fips.us-west-2.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "default-pattern-service.af-south-1.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "default-pattern-service-fips.af-south-1.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "aws-global",
            "fips": False,
            "dualstack": False,
            "endpoint": "global-service.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "aws-global",
            "fips": True,
            "dualstack": False,
            "endpoint": "global-service-fips.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "foo",
            "fips": False,
            "dualstack": False,
            "endpoint": "global-service.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "foo",
            "fips": True,
            "dualstack": False,
            "endpoint": "global-service-fips.amazonaws.com",
        },
        {
            "service": "override-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.override-variant-service.us-west-2.new.dns.suffix",
        },
        {
            "service": "override-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.override-variant-service.af-south-1.new.dns.suffix",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service-fips.us-west-2.new.dns.suffix",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service-fips.af-south-1.new.dns.suffix",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-hostname-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.override-variant-hostname-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-hostname-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.override-variant-hostname-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-endpoint-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.override-endpoint-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-endpoint-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "override-endpoint-variant-service-fips.af-south-1.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "default-pattern-service.us-west-2.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "default-pattern-service.us-west-2.api.aws",
        },
        {
            "service": "default-pattern-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "default-pattern-service.af-south-1.amazonaws.com",
        },
        {
            "service": "default-pattern-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "default-pattern-service.af-south-1.api.aws",
        },
        {
            "service": "global-service",
            "region": "aws-global",
            "fips": False,
            "dualstack": False,
            "endpoint": "global-service.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "aws-global",
            "fips": False,
            "dualstack": True,
            "endpoint": "global-service.api.aws",
        },
        {
            "service": "global-service",
            "region": "foo",
            "fips": False,
            "dualstack": False,
            "endpoint": "global-service.amazonaws.com",
        },
        {
            "service": "global-service",
            "region": "foo",
            "fips": False,
            "dualstack": True,
            "endpoint": "global-service.api.aws",
        },
        {
            "service": "override-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-service.dualstack.us-west-2.new.dns.suffix",
        },
        {
            "service": "override-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-service.dualstack.af-south-1.new.dns.suffix",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-dns-suffix-service.us-west-2.new.dns.suffix",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-dns-suffix-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-dns-suffix-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-dns-suffix-service.af-south-1.new.dns.suffix",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-hostname-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-hostname-service.dualstack.us-west-2.api.aws",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-variant-hostname-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-variant-hostname-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-variant-hostname-service.dualstack.af-south-1.api.aws",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-endpoint-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-endpoint-variant-service.dualstack.us-west-2.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "override-endpoint-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "override-endpoint-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "override-endpoint-variant-service.af-south-1.api.aws",
        },
        {
            "service": "multi-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": False,
            "endpoint": "multi-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "multi-variant-service",
            "region": "us-west-2",
            "fips": False,
            "dualstack": True,
            "endpoint": "multi-variant-service.dualstack.us-west-2.api.aws",
        },
        {
            "service": "multi-variant-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.multi-variant-service.us-west-2.amazonaws.com",
        },
        {
            "service": "multi-variant-service",
            "region": "us-west-2",
            "fips": True,
            "dualstack": True,
            "endpoint": "fips.multi-variant-service.dualstack.us-west-2.new.dns.suffix",
        },
        {
            "service": "multi-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": False,
            "endpoint": "multi-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "multi-variant-service",
            "region": "af-south-1",
            "fips": False,
            "dualstack": True,
            "endpoint": "multi-variant-service.dualstack.af-south-1.api.aws",
        },
        {
            "service": "multi-variant-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": False,
            "endpoint": "fips.multi-variant-service.af-south-1.amazonaws.com",
        },
        {
            "service": "multi-variant-service",
            "region": "af-south-1",
            "fips": True,
            "dualstack": True,
            "endpoint": "fips.multi-variant-service.dualstack.af-south-1.new.dns.suffix",
        },
    ]


def _modeled_variants_template():
    return {
        "partitions": [
            {
                "defaults": {
                    "hostname": "{service}.{region}.{dnsSuffix}",
                    "protocols": ["https"],
                    "signatureVersions": ["v4"],
                    "variants": [
                        {
                            "dnsSuffix": "amazonaws.com",
                            "hostname": "{service}-fips.{region}.{dnsSuffix}",
                            "tags": ["fips"],
                        },
                        {
                            "dnsSuffix": "api.aws",
                            "hostname": "{service}.{region}.{dnsSuffix}",
                            "tags": ["dualstack"],
                        },
                        {
                            "dnsSuffix": "api.aws",
                            "hostname": "{service}-fips.{region}.{dnsSuffix}",
                            "tags": ["dualstack", "fips"],
                        },
                    ],
                },
                "dnsSuffix": "amazonaws.com",
                "partition": "aws",
                "regionRegex": "^(us|eu|ap|sa|ca|me|af)\\-\\w+\\-\\d+$",
                "regions": {
                    "af-south-1": {"description": "Africa (Cape Town)"},
                    "us-west-2": {"description": "US West (Oregon)"},
                },
                "services": {
                    "default-pattern-service": {
                        "endpoints": {
                            "af-south-1": {},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "default-pattern-service-fips.us-west-2.amazonaws.com",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "default-pattern-service.us-west-2.api.aws",
                                        "tags": ["dualstack"],
                                    },
                                ]
                            },
                        }
                    },
                    "global-service": {
                        "endpoints": {
                            "aws-global": {
                                "credentialScope": {"region": "us-east-1"},
                                "hostname": "global-service.amazonaws.com",
                                "variants": [
                                    {
                                        "hostname": "global-service-fips.amazonaws.com",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "global-service.api.aws",
                                        "tags": ["dualstack"],
                                    },
                                ],
                            }
                        },
                        "isRegionalized": False,
                        "partitionEndpoint": "aws-global",
                    },
                    "override-variant-service": {
                        "defaults": {
                            "variants": [
                                {
                                    "hostname": "fips.{service}.{region}.{dnsSuffix}",
                                    "dnsSuffix": "new.dns.suffix",
                                    "tags": ["fips"],
                                },
                                {
                                    "hostname": "{service}.dualstack.{region}.{dnsSuffix}",
                                    "dnsSuffix": "new.dns.suffix",
                                    "tags": ["dualstack"],
                                },
                            ]
                        },
                        "endpoints": {
                            "af-south-1": {},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "fips.override-variant-service.us-west-2.new.dns.suffix",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "override-variant-service.dualstack.us-west-2.new.dns.suffix",
                                        "tags": ["dualstack"],
                                    },
                                ]
                            },
                        },
                    },
                    "override-variant-dns-suffix-service": {
                        "defaults": {
                            "variants": [
                                {
                                    "dnsSuffix": "new.dns.suffix",
                                    "tags": ["fips"],
                                },
                                {
                                    "dnsSuffix": "new.dns.suffix",
                                    "tags": ["dualstack"],
                                },
                            ]
                        },
                        "endpoints": {
                            "af-south-1": {},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "override-variant-dns-suffix-service-fips.us-west-2.new.dns.suffix",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "override-variant-dns-suffix-service.us-west-2.new.dns.suffix",
                                        "tags": ["dualstack"],
                                    },
                                ]
                            },
                        },
                    },
                    "override-variant-hostname-service": {
                        "defaults": {
                            "variants": [
                                {
                                    "hostname": "fips.{service}.{region}.{dnsSuffix}",
                                    "tags": ["fips"],
                                },
                                {
                                    "hostname": "{service}.dualstack.{region}.{dnsSuffix}",
                                    "tags": ["dualstack"],
                                },
                            ]
                        },
                        "endpoints": {
                            "af-south-1": {},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "fips.override-variant-hostname-service.us-west-2.amazonaws.com",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "override-variant-hostname-service.dualstack.us-west-2.api.aws",
                                        "tags": ["dualstack"],
                                    },
                                ]
                            },
                        },
                    },
                    "override-endpoint-variant-service": {
                        "endpoints": {
                            "af-south-1": {},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "fips.override-endpoint-variant-service.us-west-2.amazonaws.com",
                                        "tags": ["fips"],
                                    },
                                    {
                                        "hostname": "override-endpoint-variant-service.dualstack.us-west-2.amazonaws.com",
                                        "tags": ["dualstack"],
                                    },
                                ]
                            },
                        }
                    },
                    "multi-variant-service": {
                        "defaults": {
                            "variants": [
                                {
                                    "hostname": "fips.{service}.{region}.{dnsSuffix}",
                                    "tags": ["fips"],
                                },
                                {
                                    "hostname": "{service}.dualstack.{region}.{dnsSuffix}",
                                    "tags": ["dualstack"],
                                },
                                {
                                    "dnsSuffix": "new.dns.suffix",
                                    "hostname": "fips.{service}.dualstack.{region}.{dnsSuffix}",
                                    "tags": ["fips", "dualstack"],
                                },
                            ]
                        },
                        "endpoints": {
                            "af-south-1": {"deprecated": True},
                            "us-west-2": {
                                "variants": [
                                    {
                                        "hostname": "fips.multi-variant-service.dualstack.us-west-2.new.dns.suffix",
                                        "tags": ["fips", "dualstack"],
                                    }
                                ]
                            },
                        },
                    },
                },
            },
            {
                "defaults": {
                    "hostname": "{service}.{region}.{dnsSuffix}",
                    "protocols": ["https"],
                    "signatureVersions": ["v4"],
                },
                "dnsSuffix": "c2s.ic.gov",
                "partition": "aws-iso",
                "regionRegex": "^us\\-iso\\-\\w+\\-\\d+$",
                "regions": {"us-iso-east-1": {"description": "US ISO East"}},
                "services": {
                    "some-service": {"endpoints": {"us-iso-east-1": {}}}
                },
            },
        ],
        "version": 3,
    }


@pytest.mark.parametrize("test_case", _variant_test_definitions())
def test_modeled_variants(test_case):
    _verify_expected_endpoint(**test_case)


def _verify_expected_endpoint(service, region, fips, dualstack, endpoint):
    resolver = regions.EndpointResolver(_modeled_variants_template())
    resolved = resolver.construct_endpoint(
        service,
        region,
        use_dualstack_endpoint=dualstack,
        use_fips_endpoint=fips,
    )
    # If we can't resolve the region, we attempt to get a
    # global endpoint.
    if not resolved:
        resolved = resolver.construct_endpoint(
            service,
            region,
            partition_name='aws',
            use_dualstack_endpoint=dualstack,
            use_fips_endpoint=fips,
        )
    assert resolved['hostname'] == endpoint


def test_additional_endpoint_data_exists_with_variants():
    resolver = regions.EndpointResolver(_modeled_variants_template())
    resolved = resolver.construct_endpoint(
        'global-service',
        'aws-global',
        use_fips_endpoint=True,
    )
    assert resolved['credentialScope'] == {'region': 'us-east-1'}
