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
import sys

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

    def test_long_value(self):
        # MAXSIZE is the max size of an int on python 2 and the maximum size
        # of Py_ssize_t on python 3, but notably not the maximum size of an
        # int since they are effectively unbounded.
        long_value = sys.maxsize + 1
        runtime_config = self.build_config_with(
            multipart_threshold=long_value)
        self.assertEqual(runtime_config['multipart_threshold'], long_value)

    def test_converts_max_bandwidth_as_string(self):
        runtime_config = self.build_config_with(max_bandwidth='1MB/s')
        self.assertEqual(runtime_config['max_bandwidth'], 1024 * 1024)

    def test_validates_max_bandwidth_no_seconds(self):
        with self.assertRaises(transferconfig.InvalidConfigError):
            self.build_config_with(max_bandwidth='1MB')

    def test_validates_max_bandwidth_in_bits_per_second(self):
        with self.assertRaises(transferconfig.InvalidConfigError):
            self.build_config_with(max_bandwidth='1Mb/s')


class TestConvertToS3TransferConfig(unittest.TestCase):
    def test_convert(self):
        runtime_config = {
            'multipart_threshold': 1,
            'multipart_chunksize': 2,
            'max_concurrent_requests': 3,
            'max_queue_size': 4,
            'max_bandwidth': 1024 * 1024,
            'addressing_style': 'path',
            'use_accelerate_endpoint': True,
            # This is a TransferConfig only option, it should
            # just be ignored if it's in the ~/.aws/config for now.
            'max_in_memory_upload_chunks': 1000,
        }
        result = transferconfig.create_transfer_config_from_runtime_config(
            runtime_config)
        self.assertEqual(result.multipart_threshold, 1)
        self.assertEqual(result.multipart_chunksize, 2)
        self.assertEqual(result.max_request_concurrency, 3)
        self.assertEqual(result.max_request_queue_size, 4)
        self.assertEqual(result.max_bandwidth, 1024 * 1024)
        self.assertNotEqual(result.max_in_memory_upload_chunks, 1000)
