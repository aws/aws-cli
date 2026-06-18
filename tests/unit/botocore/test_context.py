# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest

from botocore.context import (
    ClientContext,
    get_context,
    reset_context,
    set_context,
    start_as_current_context,
    with_current_context,
)


@pytest.fixture
def custom_context():
    ctx = ClientContext()
    ctx.features.add('CUSTOM')
    return ctx


class TestContext:
    def test_get_context_returns_none(self):
        ctx = get_context()
        assert ctx is None

    def test_get_context_returns_current(self, client_context):
        ctx = get_context()
        assert ctx == client_context

    def test_set_context(self, custom_context):
        token = set_context(custom_context)
        ctx = get_context()
        assert ctx == custom_context
        reset_context(token)

    def test_start_as_current_context(self):
        with start_as_current_context():
            ctx = get_context()
            ctx.features.add('FOO')
            assert ctx.features == {'FOO'}
        ctx = get_context()
        assert ctx is None

    def test_nested_start_as_current_context(self):
        with start_as_current_context():
            ctx = get_context()
            ctx.features.add('FOO')
            with start_as_current_context():
                ctx = get_context()
                ctx.features.add('BAR')
                assert ctx.features == {'FOO', 'BAR'}
            ctx = get_context()
            assert ctx.features == {'FOO'}
        ctx = get_context()
        assert ctx is None

    def test_start_as_current_context_with_param(self, custom_context):
        with start_as_current_context(custom_context):
            ctx = get_context()
            assert ctx.features == {'CUSTOM'}

    def test_with_current_context(self):
        @with_current_context()
        def do_something():
            ctx = get_context()
            assert ctx is not None

        do_something()

    def test_with_current_context_with_hook(self):
        def register_fake():
            ctx = get_context()
            ctx.features.add('FOO')

        @with_current_context(register_fake)
        def do_something():
            ctx = get_context()
            assert ctx.features == {'FOO'}

        do_something()
