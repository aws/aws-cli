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

from awscli.customizations.s3 import constants
from awscli.customizations.s3.utils import human_readable_to_int
# If the user does not specify any overrides,
# these are the default values we use for the s3 transfer
# commands.
import logging


LOGGER = logging.getLogger(__name__)

DEFAULTS = {
    'multipart_threshold': 8 * (1024 ** 2),
    'multipart_chunksize': 8 * (1024 ** 2),
    'max_concurrent_requests': 10,
    'max_queue_size': 1000,
    'max_bandwidth': None,
    'preferred_transfer_client': constants.AUTO_RESOLVE_TRANSFER_CLIENT,
    'target_bandwidth': None,
}


class InvalidConfigError(Exception):
    pass


class RuntimeConfig(object):

    POSITIVE_INTEGERS = ['multipart_chunksize', 'multipart_threshold',
                         'max_concurrent_requests', 'max_queue_size',
                         'max_bandwidth', 'target_bandwidth']
    HUMAN_READABLE_SIZES = ['multipart_chunksize', 'multipart_threshold']
    HUMAN_READABLE_RATES = ['max_bandwidth', 'target_bandwidth']
    SUPPORTED_CHOICES = {
        'preferred_transfer_client': [
            constants.AUTO_RESOLVE_TRANSFER_CLIENT,
            constants.CLASSIC_TRANSFER_CLIENT,
            constants.CRT_TRANSFER_CLIENT,
        ]
    }
    CHOICE_ALIASES = {
        'preferred_transfer_client': {
            'default': constants.CLASSIC_TRANSFER_CLIENT
        }
    }

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
        self._resolve_choice_aliases(runtime_config)
        self._validate_config(runtime_config)
        return runtime_config

    def _convert_human_readable_sizes(self, runtime_config):
        for attr in self.HUMAN_READABLE_SIZES:
            value = runtime_config.get(attr)
            if value is not None and not isinstance(value, int):
                runtime_config[attr] = human_readable_to_int(value)

    def _convert_human_readable_rates(self, runtime_config):
        for attr in self.HUMAN_READABLE_RATES:
            value = runtime_config.get(attr)
            if value is not None and not isinstance(value, int):
                if value.endswith('B/s'):
                    runtime_config[attr] = self._human_readable_rate_to_int(
                        value
                    )
                elif value.endswith('b/s'):
                    bits_per_sec = self._human_readable_rate_to_int(value)
                    bytes_per_sec = int(bits_per_sec / 8)
                    runtime_config[attr] = bytes_per_sec
                elif self._is_integer_str(value):
                    runtime_config[attr] = int(value)
                else:
                    raise InvalidConfigError(
                        'Invalid rate: %s. The value must be expressed '
                        'as an integer in terms of bytes per second '
                        '(e.g. 10485760) or a rate in terms of bytes '
                        'per second (e.g. 10MB/s or 800KB/s) or bits per '
                        'second (e.g. 10Mb/s or 800Kb/s)' % value)

    def _human_readable_rate_to_int(self, value):
        # The human_readable_to_int() utility only supports integers (e.g. 1024)
        # as strings and human readable sizes (e.g. 10MB, 5GB). It does not
        # directly support human readable rates (e.g. 10MB/s, 5GB/s) nor human
        # readable sizes that do not contain a magnitude prefix (e.g. 1024B).
        # However, the rate configuration require the values end with "/s"
        # and allows for values that do not have a magnitude prefix
        # (e.g. 1024B/s).
        #
        # To account for these limitations:
        #
        # 1. If the human readable rate does not contain a magnitude prefix, it
        #    will strip the "B/s" to provide the value as an integer string to
        #    human_readable_int() (e.g. "1024B/s" -> "1024")
        #
        # 2. Otherwise, it will strip the "/s" to provide the value as a
        #    human readable size to human_readable_int()
        #    (e.g. "1024MB/s -> "1024MB")
        if self._is_integer_str(value[:-3]):
            return human_readable_to_int(value[:-3])
        return human_readable_to_int(value[:-2])

    def _is_integer_str(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _resolve_choice_aliases(self, runtime_config):
        for attr in self.CHOICE_ALIASES:
            current_value = runtime_config.get(attr)
            if current_value in self.CHOICE_ALIASES[attr]:
                resolved_value = self.CHOICE_ALIASES[attr][current_value]
                LOGGER.debug(
                    'Resolved %s configuration alias value "%s" to "%s"',
                    attr, current_value, resolved_value
                )
                runtime_config[attr] = resolved_value

    def _validate_config(self, runtime_config):
        self._validate_positive_integers(runtime_config)
        self._validate_choices(runtime_config)

    def _validate_positive_integers(self, runtime_config):
        for attr in self.POSITIVE_INTEGERS:
            value = runtime_config.get(attr)
            if value is not None:
                try:
                    runtime_config[attr] = int(value)
                    if not runtime_config[attr] > 0:
                        self._error_positive_value(attr, value)
                except ValueError:
                    self._error_positive_value(attr, value)

    def _validate_choices(self, runtime_config):
        for attr in self.SUPPORTED_CHOICES:
            value = runtime_config.get(attr)
            if value is not None:
                if value not in self.SUPPORTED_CHOICES[attr]:
                    self._error_invalid_choice(attr, value)

    def _error_positive_value(self, name, value):
        raise InvalidConfigError(
            "Value for %s must be a positive integer: %s" % (name, value))

    def _error_invalid_choice(self, name, value):
        raise InvalidConfigError(
            f'Invalid value: "{value}" for configuration option: "{name}". '
            f'Supported values are: {", ".join(self.SUPPORTED_CHOICES[name])}'
        )


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
