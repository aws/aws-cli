# Copyright 2012-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore import translate
from tests import unittest


class TestBuildRetryConfig(unittest.TestCase):
    def setUp(self):
        self.retry = {
            "definitions": {"def_name": {"from": {"definition": "file"}}},
            "retry": {
                "__default__": {
                    "max_attempts": 5,
                    "delay": "global_delay",
                    "policies": {
                        "global_one": "global",
                        "override_me": "global",
                    },
                },
                "sts": {
                    "__default__": {
                        "delay": "service_specific_delay",
                        "policies": {
                            "service_one": "service",
                            "override_me": "service",
                        },
                    },
                    "AssumeRole": {
                        "policies": {
                            "name": "policy",
                            "other": {"$ref": "def_name"},
                        }
                    },
                },
            },
        }

    def test_inject_retry_config(self):
        retry = translate.build_retry_config(
            'sts', self.retry['retry'], self.retry['definitions']
        )
        self.assertIn('__default__', retry)
        self.assertEqual(
            retry['__default__'],
            {
                "max_attempts": 5,
                "delay": "service_specific_delay",
                "policies": {
                    "global_one": "global",
                    "override_me": "service",
                    "service_one": "service",
                },
            },
        )
        # Policies should be merged.
        operation_config = retry['AssumeRole']
        self.assertEqual(operation_config['policies']['name'], 'policy')

    def test_resolve_reference(self):
        retry = translate.build_retry_config(
            'sts', self.retry['retry'], self.retry['definitions']
        )
        operation_config = retry['AssumeRole']
        # And we should resolve references.
        self.assertEqual(
            operation_config['policies']['other'],
            {"from": {"definition": "file"}},
        )

    def test_service_specific_defaults_no_mutate_default_retry(self):
        retry = translate.build_retry_config(
            'sts', self.retry['retry'], self.retry['definitions']
        )
        # sts has a specific policy
        self.assertEqual(
            retry['__default__'],
            {
                "max_attempts": 5,
                "delay": "service_specific_delay",
                "policies": {
                    "global_one": "global",
                    "override_me": "service",
                    "service_one": "service",
                },
            },
        )

        # The general defaults for the upstream model should not have been
        # mutated from building the retry config
        self.assertEqual(
            self.retry['retry']['__default__'],
            {
                "max_attempts": 5,
                "delay": "global_delay",
                "policies": {
                    "global_one": "global",
                    "override_me": "global",
                },
            },
        )

    def test_client_override_max_attempts(self):
        retry = translate.build_retry_config(
            'sts',
            self.retry['retry'],
            self.retry['definitions'],
            client_retry_config={'max_attempts': 9},
        )
        self.assertEqual(retry['__default__']['max_attempts'], 10)
        # But it should not mutate the original retry model
        self.assertEqual(self.retry['retry']['__default__']['max_attempts'], 5)
