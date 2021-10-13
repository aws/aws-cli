# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest

import awscli.logger


@pytest.fixture(autouse=True)
def clear_loggers():
    """Ensure all loggers have no residual state before test runs

    Some tests rely on updating the built-in logger and so we want to make
    sure that any residual state is cleared between test cases such as making
    sure there are no handlers and the logger level is reset to not set.
    """
    loggers = [name for name in logging.root.manager.loggerDict]
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.setLevel(logging.NOTSET)
    awscli.logger.disable_crt_logging()
