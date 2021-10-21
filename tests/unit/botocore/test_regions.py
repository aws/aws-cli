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
from tests import unittest

from botocore import regions
from botocore.exceptions import NoRegionError


class TestEndpointResolver(unittest.TestCase):
    def _template(self):
        return {
            'partitions': [
                {
                    'partition': 'aws',
                    'dnsSuffix': 'amazonaws.com',
                    'regionRegex': r'^(us|eu)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}'
                    },
                    'regions': {
                        'us-foo': {'regionName': 'a'},
                        'us-bar': {'regionName': 'b'},
                        'eu-baz': {'regionName': 'd'}
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'us-foo': {},
                                'us-bar': {},
                                'eu-baz': {},
                                'd': {}
                            }
                        },
                        's3': {
                            'defaults': {
                                'sslCommonName': \
                                    '{service}.{region}.{dnsSuffix}'
                            },
                            'endpoints': {
                                'us-foo': {
                                    'sslCommonName': \
                                        '{region}.{service}.{dnsSuffix}'
                                },
                                'us-bar': {},
                                'eu-baz': {'hostname': 'foo'}
                            }
                        },
                        'not-regionalized': {
                            'isRegionalized': False,
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'not-regionalized'},
                                'us-foo': {},
                                'eu-baz': {}
                            }
                        },
                        'non-partition': {
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'host'},
                                'us-foo': {}
                            }
                        },
                        'merge': {
                            'defaults': {
                                'signatureVersions': ['v2'],
                                'protocols': ['http']
                            },
                            'endpoints': {
                                'us-foo': {'signatureVersions': ['v4']},
                                'us-bar': {'protocols': ['https']}
                            }
                        }
                    }
                },
                {
                    'partition': 'foo',
                    'dnsSuffix': 'foo.com',
                    'regionRegex': r'^(foo)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}',
                        'protocols': ['http'],
                        'foo': 'bar'
                    },
                    'regions': {
                        'foo-1': {'regionName': '1'},
                        'foo-2': {'regionName': '2'},
                        'foo-3': {'regionName': '3'}
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'foo-1': {
                                    'foo': 'baz'
                                },
                                'foo-2': {},
                                'foo-3': {}
                            }
                        }
                    }
                }
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
            'ec2', allow_non_regional=True)
        self.assertEqual(['d', 'eu-baz', 'us-bar', 'us-foo'], sorted(result))

    def test_gets_endpoint_names_for_partition(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=True, partition_name='foo')
        self.assertEqual(['foo-1', 'foo-2', 'foo-3'], sorted(result))

    def test_list_regional_endpoints_only(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=False)
        self.assertEqual(['eu-baz', 'us-bar', 'us-foo'], sorted(result))

    def test_returns_none_when_no_match(self):
        resolver = regions.EndpointResolver(self._template())
        self.assertIsNone(resolver.construct_endpoint('foo', 'baz'))

    def test_constructs_regionalized_endpoints_for_exact_matches(self):
        resolver = regions.EndpointResolver(self._template())
        result = resolver.construct_endpoint('not-regionalized', 'eu-baz')
        self.assertEqual('not-regionalized.eu-baz.amazonaws.com',
                          result['hostname'])
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
