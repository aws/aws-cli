# Copyright 2013-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from s3transfer.manager import TransferConfig

from awscli.customizations.s3.utils import human_readable_to_bytes
# If the user does not specify any overrides,
# these are the default values we use for the s3 transfer
# commands.
DEFAULTS = {
    'multipart_threshold': 8 * (1024 ** 2),
    'multipart_chunksize': 8 * (1024 ** 2),
    'max_concurrent_requests': 10,
    'max_queue_size': 1000,
    'max_bandwidth': None
}


class InvalidConfigError(Exception):
    pass


class RuntimeConfig(object):

    POSITIVE_INTEGERS = ['multipart_chunksize', 'multipart_threshold',
                         'max_concurrent_requests', 'max_queue_size',
                         'max_bandwidth']
    HUMAN_READABLE_SIZES = ['multipart_chunksize', 'multipart_threshold']
    HUMAN_READABLE_RATES = ['max_bandwidth']

    @staticmethod
    def defaults():
        return DEFAULTS.copy()

    def build_config(self, **kwargs):
        """Create and convert a runtime config dictionary.

        This method will merge and convert S3 runtime configuration
        data into a single dictionary that can then be passed to classes
        that use this runtime config.

        :param kwargs:  Any key in the ``DEFAULTS`` dict.
        :return: A dictionary of the merged and converted values.

        """
        runtime_config = DEFAULTS.copy()
        if kwargs:
            runtime_config.update(kwargs)
        self._convert_human_readable_sizes(runtime_config)
        self._convert_human_readable_rates(runtime_config)
        self._validate_config(runtime_config)
        return runtime_config

    def _convert_human_readable_sizes(self, runtime_config):
        for attr in self.HUMAN_READABLE_SIZES:
            value = runtime_config.get(attr)
            if value is not None and not isinstance(value, int):
                runtime_config[attr] = human_readable_to_bytes(value)

    def _convert_human_readable_rates(self, runtime_config):
        for attr in self.HUMAN_READABLE_RATES:
            value = runtime_config.get(attr)
            if value is not None and not isinstance(value, int):
                if not value.endswith('B/s'):
                    raise InvalidConfigError(
                        'Invalid rate: %s. The value must be expressed '
                        'as a rate in terms of bytes per seconds '
                        '(e.g. 10MB/s or 800KB/s)' % value)
                runtime_config[attr] = human_readable_to_bytes(value[:-2])

    def _validate_config(self, runtime_config):
        for attr in self.POSITIVE_INTEGERS:
            value = runtime_config.get(attr)
            if value is not None:
                try:
                    runtime_config[attr] = int(value)
                    if not runtime_config[attr] > 0:
                        self._error_positive_value(attr, value)
                except ValueError:
                    self._error_positive_value(attr, value)

    def _error_positive_value(self, name, value):
        raise InvalidConfigError(
            "Value for %s must be a positive integer: %s" % (name, value))


def create_transfer_config_from_runtime_config(runtime_config):
    """
    Creates an equivalent s3transfer TransferConfig

    :type runtime_config: dict
    :argument runtime_config: A valid RuntimeConfig-generated dict.

    :returns: A TransferConfig with the same configuration as the runtime
        config.
    """
    translation_map = {
        'max_concurrent_requests': 'max_request_concurrency',
        'max_queue_size': 'max_request_queue_size',
        'multipart_threshold': 'multipart_threshold',
        'multipart_chunksize': 'multipart_chunksize',
        'max_bandwidth': 'max_bandwidth',
    }
    kwargs = {}
    for key, value in runtime_config.items():
        if key not in translation_map:
            continue
        kwargs[translation_map[key]] = value
    return TransferConfig(**kwargs)
