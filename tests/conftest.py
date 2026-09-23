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
import collections
import logging
import platform

import pytest
from botocore.model import OperationModel
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

import awscli.logger
from awscli.clidriver import ServiceCommand, create_clidriver


@pytest.fixture
def cli_driver():
    # Each model-validation command gets its own driver so previously checked
    # command tables and models do not accumulate in a module-wide cache.
    return create_clidriver()


@pytest.fixture(scope='session')
def service_command_names():
    """Map each botocore service name to the top-level CLI command bound to
    it, built once per process from a throwaway driver."""
    # A command whose name is a botocore service name is assumed to be bound
    # to that service; iter_operation_commands verifies this before yielding,
    # so only renamed commands need their model loaded here.
    driver = create_clidriver()
    available = set(driver.session.get_available_services())
    names = {}
    command_table = driver.create_help_command().command_table
    for command_name, command in command_table.items():
        if not isinstance(command, ServiceCommand):
            continue
        if command_name in available:
            service_name = command_name
        else:
            service_name = command.service_model.service_name
        if service_name in names:
            raise RuntimeError(
                f'Service {service_name!r} is bound to both the '
                f'{names[service_name]!r} and {command_name!r} commands.'
            )
        names[service_name] = command_name
    if not names:
        raise RuntimeError(
            'The top-level command table has no ServiceCommand entries, so '
            'service commands cannot be looked up by service name.'
        )
    return names


@pytest.fixture(scope='session')
def iter_operation_commands():
    # Session scoped so that module-scoped fixtures can depend on it.

    def iter_commands(driver, command_name, service_name):
        """Yield (command_name, sub_name, sub_command, operation_model) for
        every model-backed sub-command of a top-level CLI command, after
        checking that the command is bound to the given botocore service."""
        command = driver.create_help_command().command_table[command_name]
        actual = command.service_model.service_name
        if actual != service_name:
            raise RuntimeError(
                f'CLI command {command_name!r} is bound to service '
                f'{actual!r}, not {service_name!r}'
            )
        sub_table = command.create_help_command().command_table
        for sub_name, sub_command in sub_table.items():
            obj = sub_command.create_help_command().obj
            if isinstance(obj, OperationModel):
                yield command_name, sub_name, sub_command, obj

    return iter_commands


@pytest.fixture(autouse=True)
def validates_models_properties_are_unique(request):
    # An internal build system parses the JUnitXML report of validates_models
    # tests and needs one aws_service/aws_operation/shape set per testcase, so
    # a property recorded twice in one test would misattribute a failure.
    yield
    if request.node.get_closest_marker('validates_models') is None:
        return
    counts = collections.Counter(
        name for name, _ in request.node.user_properties
    )
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        pytest.fail(
            'validates_models tests must record each property at most once '
            f'per testcase; duplicates: {duplicates}'
        )


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
        if logger.level != logging.NOTSET:
            logger.setLevel(logging.NOTSET)
    # setLevel clears every logger's effective-level cache. Do this once even
    # when no levels changed, rather than once per already-reset logger.
    logging.root.setLevel(logging.root.level)
    awscli.logger.disable_crt_logging()


@pytest.fixture
def ptk_app_session():
    with create_pipe_input() as pipe_input:
        output = DummyOutput()
        try:
            with create_app_session(
                input=pipe_input, output=output
            ) as session:
                yield session
        finally:
            pipe_input.close()
