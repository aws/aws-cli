# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.testutils import unittest

from awscli.customizations.s3 import transferconfig


class TestTransferConfig(unittest.TestCase):

    def build_config_with(self, **config_from_user):
        return transferconfig.RuntimeConfig().build_config(**config_from_user)

    def test_user_provides_no_config_uses_default(self):
        # If the user does not provide any config overrides,
        # we should just use the default values defined in
        # the module.
        config = transferconfig.RuntimeConfig()
        runtime_config = config.build_config()
        self.assertEqual(runtime_config, transferconfig.DEFAULTS)

    def test_user_provides_partial_overrides(self):
        config_from_user = {
            'max_concurrent_requests': '20',
            'multipart_threshold': str(64 * (1024 ** 2)),
        }
        runtime_config = self.build_config_with(**config_from_user)
        # Our overrides were accepted.
        self.assertEqual(runtime_config['multipart_threshold'],
                         int(config_from_user['multipart_threshold']))
        self.assertEqual(runtime_config['max_concurrent_requests'],
                         int(config_from_user['max_concurrent_requests']))
        # And defaults were used for values not specified.
        self.assertEqual(runtime_config['max_queue_size'],
                         int(transferconfig.DEFAULTS['max_queue_size']))

    def test_validates_integer_types(self):
        with self.assertRaises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="not an int")

    def test_validates_positive_integers(self):
        with self.assertRaises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="-10")

    def test_min_value(self):
        with self.assertRaises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="0")

    def test_human_readable_sizes_converted_to_bytes(self):
        runtime_config = self.build_config_with(multipart_threshold="10MB")
        self.assertEqual(runtime_config['multipart_threshold'],
                         10 * 1024 * 1024)
