# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging

import awscrt.io

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def set_stream_logger(logger_name, log_level, stream=None,
                      format_string=None):
    """
    Convenience method to configure a stream logger.

    :type logger_name: str
    :param logger_name: The name of the logger to configure

    :type log_level: str
    :param log_level: The log level to set for the logger.  This
        is any param supported by the ``.setLevel()`` method of
        a ``Log`` object.

    :type stream: file
    :param stream: A file like object to log to.  If none is provided
        then sys.stderr will be used.

    :type format_string: str
    :param format_string: The format string to use for the log
        formatter.  If none is provided this will default to
        ``self.LOG_FORMAT``.

    """
    log = logging.getLogger(logger_name)
    log.setLevel(logging.DEBUG)

    remove_stream_logger(logger_name)

    handler_name = f'{logger_name}_stream_handler'
    ch = logging.StreamHandler(stream)
    ch.set_name(handler_name)
    ch.setLevel(log_level)

    # create formatter
    if format_string is None:
        format_string = LOG_FORMAT
    formatter = logging.Formatter(format_string)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    log.addHandler(ch)


def remove_stream_logger(logger_name):
    """
    Convenience method to configure a stream logger.

    :type logger_name: str
    :param logger_name: The name of the logger to configure

    """
    log = logging.getLogger(logger_name)
    handler_name = f'{logger_name}_stream_handler'
    for handler in log.handlers:
        if handler.get_name() == handler_name:
            log.removeHandler(handler)


def enable_crt_logging():
    awscrt.io.init_logging(awscrt.io.LogLevel.Debug, 'stderr')


def disable_crt_logging():
    awscrt.io.init_logging(awscrt.io.LogLevel.NoLogs, 'stderr')
