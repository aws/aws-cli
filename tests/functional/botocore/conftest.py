# Copyright 2012-2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from tests import create_session


@pytest.fixture()
def patched_session(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'access_key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret_key')
    monkeypatch.setenv('AWS_CONFIG_FILE', 'no-exist-foo')
    monkeypatch.delenv('AWS_PROFILE', raising=False)
    monkeypatch.delenv('AWS_DEFAULT_REGION', raising=False)
    session = create_session()
    return session
