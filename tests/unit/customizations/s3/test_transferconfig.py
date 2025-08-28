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

import pytest

from awscli.customizations.s3 import transferconfig


class TestTransferConfig:
    def build_config_with(self, **config_from_user):
        return transferconfig.RuntimeConfig().build_config(**config_from_user)

    def test_user_provides_no_config_uses_default(self):
        # If the user does not provide any config overrides,
        # we should just use the default values defined in
        # the module.
        config = transferconfig.RuntimeConfig()
        runtime_config = config.build_config()
        assert runtime_config == transferconfig.DEFAULTS

    def test_user_provides_partial_overrides(self):
        config_from_user = {
            'max_concurrent_requests': '20',
            'multipart_threshold': str(64 * (1024**2)),
        }
        runtime_config = self.build_config_with(**config_from_user)
        # Our overrides were accepted.
        assert runtime_config['multipart_threshold'] == int(
            config_from_user['multipart_threshold']
        )
        assert runtime_config['max_concurrent_requests'] == int(
            config_from_user['max_concurrent_requests']
        )
        # And defaults were used for values not specified.
        assert runtime_config['max_queue_size'] == int(
            transferconfig.DEFAULTS['max_queue_size']
        )

    def test_validates_integer_types(self):
        with pytest.raises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="not an int")

    def test_validates_positive_integers(self):
        with pytest.raises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="-10")

    def test_min_value(self):
        with pytest.raises(transferconfig.InvalidConfigError):
            self.build_config_with(max_concurrent_requests="0")

    def test_human_readable_sizes_converted_to_bytes(self):
        runtime_config = self.build_config_with(multipart_threshold="10MB")
        assert runtime_config['multipart_threshold'] == 10 * 1024 * 1024

    def test_long_value(self):
        # MAXSIZE is the max size of an int on python 2 and the maximum size
        # of Py_ssize_t on python 3, but notably not the maximum size of an
        # int since they are effectively unbounded.
        long_value = sys.maxsize + 1
        runtime_config = self.build_config_with(multipart_threshold=long_value)
        assert runtime_config['multipart_threshold'] == long_value

    @pytest.mark.parametrize(
        'provided,resolved',
        [
            (None, 'auto'),
            ('auto', 'auto'),
            ('classic', 'classic'),
            ('default', 'classic'),
            ('crt', 'crt'),
        ],
    )
    def test_set_preferred_transfer_client(self, provided, resolved):
        config_kwargs = {}
        if provided is not None:
            config_kwargs['preferred_transfer_client'] = provided
        runtime_config = self.build_config_with(**config_kwargs)
        assert runtime_config['preferred_transfer_client'] == resolved

    @pytest.mark.parametrize(
        'config_name,provided,expected',
        [
            # max_bandwidth cases
            ('max_bandwidth', '1MB/s', 1024 * 1024),
            ('max_bandwidth', '8Mb/s', 1024 * 1024),
            ('max_bandwidth', '1000', 1000),
            ('max_bandwidth', '1000B/s', 1000),
            ('max_bandwidth', '8000b/s', 1000),
            # target_bandwidth cases
            ('target_bandwidth', '5MB/s', 5 * 1024 * 1024),
            ('target_bandwidth', '1Mb/s', 1 * 1024 * 1024 / 8),
            ('target_bandwidth', '1000', 1000),
            ('target_bandwidth', '1000B/s', 1000),
            ('target_bandwidth', '8000b/s', 1000),
        ],
    )
    def test_rate_conversions(self, config_name, provided, expected):
        params = {config_name: provided}
        runtime_config = self.build_config_with(**params)
        assert runtime_config[config_name] == expected

    @pytest.mark.parametrize(
        'config_name,provided',
        [
            # max_bandwidth cases
            ('max_bandwidth', '1MB'),
            ('max_bandwidth', '1B'),
            ('max_bandwidth', '1b'),
            ('max_bandwidth', '100/s'),
            ('max_bandwidth', ''),
            ('max_bandwidth', 'value-with-no-digits'),
            # target_bandwidth cases
            ('target_bandwidth', '1MB'),
            ('target_bandwidth', '1B'),
            ('target_bandwidth', '1b'),
            ('target_bandwidth', '100/s'),
            ('target_bandwidth', ''),
            ('target_bandwidth', 'value-with-no-digits'),
        ],
    )
    def test_invalid_rate_values(self, config_name, provided):
        params = {config_name: provided}
        with pytest.raises(transferconfig.InvalidConfigError):
            self.build_config_with(**params)

    def test_validates_preferred_transfer_client_choices(self):
        with pytest.raises(transferconfig.InvalidConfigError):
            self.build_config_with(preferred_transfer_client='not-supported')


class TestConvertToS3TransferConfig:
    def test_convert(self):
        runtime_config = {
            'multipart_threshold': 1,
            'multipart_chunksize': 2,
            'max_concurrent_requests': 3,
            'max_queue_size': 4,
            'max_bandwidth': 1024 * 1024,
            'addressing_style': 'path',
            'use_accelerate_endpoint': True,
            'io_chunksize': 1024 * 1024,
            # This is a TransferConfig only option, it should
            # just be ignored if it's in the ~/.aws/config for now.
            'max_in_memory_upload_chunks': 1000,
        }
        result = transferconfig.create_transfer_config_from_runtime_config(
            runtime_config
        )
        assert result.multipart_threshold == 1
        assert result.multipart_chunksize == 2
        assert result.max_request_concurrency == 3
        assert result.max_request_queue_size == 4
        assert result.max_bandwidth == 1024 * 1024
        assert result.io_chunksize == 1024 * 1024
        assert result.max_in_memory_upload_chunks != 1000
