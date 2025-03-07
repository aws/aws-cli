# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import time
from concurrent import futures
from itertools import product

import pytest

from botocore import __version__ as botocore_version
from botocore.config import Config
from tests import ClientHTTPStubber


class UACapHTTPStubber(ClientHTTPStubber):
    """
    Wrapper for ClientHTTPStubber that captures UA header from one request.
    """

    def __init__(self, obj_with_event_emitter):
        super().__init__(obj_with_event_emitter, strict=False)
        self.add_response()  # expect exactly one request

    @property
    def captured_ua_string(self):
        if len(self.requests) > 0:
            return self.requests[0].headers['User-Agent'].decode()
        return None


@pytest.mark.parametrize(
    'sess_name, sess_version, sess_extra, cfg_extra, cfg_appid',
    # Produce every combination of User-Agent related config settings other
    # than Config.user_agent which will always be set in this test.
    product(
        ('sess_name', None),
        ('sess_version', None),
        ('sess_extra', None),
        ('cfg_extra', None),
        ('cfg_appid', None),
    ),
)
def test_user_agent_from_config_replaces_default(
    sess_name,
    sess_version,
    sess_extra,
    cfg_extra,
    cfg_appid,
    patched_session,
):
    # Config.user_agent replaces all parts of the regular User-Agent header
    # format except for itself and "extras" set in Session and Config. This
    # behavior exists to maintain backwards compatibility for clients who
    # expect an exact User-Agent header value.
    expected_str = 'my user agent str'
    if sess_name:
        patched_session.user_agent_name = sess_name
    if sess_version:
        patched_session.user_agent_version = sess_version
    if sess_extra:
        patched_session.user_agent_extra = sess_extra
        expected_str += f' {sess_extra}'
    client_cfg = Config(
        user_agent='my user agent str',
        user_agent_extra=cfg_extra,
        user_agent_appid=cfg_appid,
    )
    if cfg_extra:
        expected_str += f' {cfg_extra}'
    client_s3 = patched_session.create_client('s3', config=client_cfg)
    with UACapHTTPStubber(client_s3) as stub_client:
        client_s3.list_buckets()

    assert stub_client.captured_ua_string == expected_str


@pytest.mark.parametrize(
    'sess_name, sess_version, cfg_appid',
    # Produce every combination of User-Agent related config settings other
    # than Config.user_agent which is never set in this test
    # (``test_user_agent_from_config_replaces_default`` covers all cases where
    # it is set) and Session.user_agent_extra and Config.user_agent_extra
    # which both are always set in this test
    product(
        ('sess_name', None),
        ('sess_version', None),
        ('cfg_appid', None),
    ),
)
def test_user_agent_includes_extra(
    sess_name,
    sess_version,
    cfg_appid,
    patched_session,
):
    # Libraries and apps can use the ``Config.user_agent_extra`` and
    # ``Session.user_agent_extra`` to append arbitrary data to the User-Agent
    # header. Unless Config.user_agent is also set, these two fields should
    # always appear at the end of the header value.
    if sess_name:
        patched_session.user_agent_name = sess_name
    if sess_version:
        patched_session.user_agent_version = sess_version
    patched_session.user_agent_extra = "sess_extra"
    client_cfg = Config(
        user_agent=None,
        user_agent_extra='cfg_extra',
        user_agent_appid=cfg_appid,
    )
    client_s3 = patched_session.create_client('s3', config=client_cfg)
    with UACapHTTPStubber(client_s3) as stub_client:
        client_s3.list_buckets()

    assert stub_client.captured_ua_string.endswith(' sess_extra cfg_extra')


@pytest.mark.parametrize(
    'sess_name, sess_version, sess_extra, cfg_extra',
    # Produce every combination of User-Agent related config settings other
    # than Config.user_agent which is never set in this test and
    # Config.user_agent_appid which is always set in this test.
    product(
        ('sess_name', None),
        ('sess_version', None),
        ('sess_extra', None),
        ('cfg_extra', None),
    ),
)
def test_user_agent_includes_appid(
    sess_name,
    sess_version,
    sess_extra,
    cfg_extra,
    patched_session,
):
    # The User-Agent header string should always include the value set in
    # ``Config.user_agent_appid``, unless ``Config.user_agent`` is also set
    # (this latter case is covered in ``test_user_agent_from_config_replaces_default``).
    if sess_name:
        patched_session.user_agent_name = sess_name
    if sess_version:
        patched_session.user_agent_version = sess_version
    if sess_extra:
        patched_session.user_agent_extra = sess_extra
    client_cfg = Config(
        user_agent=None,
        user_agent_appid='123456',
        user_agent_extra=cfg_extra,
    )
    client_s3 = patched_session.create_client('s3', config=client_cfg)
    with UACapHTTPStubber(client_s3) as stub_client:
        client_s3.list_buckets()

    uafields = stub_client.captured_ua_string.split(' ')
    assert 'app/123456' in uafields


def test_user_agent_long_appid_yields_warning(patched_session, caplog):
    # user_agent_appid config values longer than 50 characters should result
    # in a warning
    sixtychars = '000000000011111111112222222222333333333344444444445555555555'
    assert len(sixtychars) > 50
    client_cfg = Config(user_agent_appid=sixtychars)
    client_s3 = patched_session.create_client('s3', config=client_cfg)
    with UACapHTTPStubber(client_s3):
        with caplog.at_level(logging.INFO):
            client_s3.list_buckets()

    assert (
        'The configured value for user_agent_appid exceeds the maximum length'
        in caplog.text
    )


def test_user_agent_appid_gets_sanitized(patched_session, caplog):
    # Parentheses are not valid characters in the user agent string
    badchars = '1234('
    client_cfg = Config(user_agent_appid=badchars)
    client_s3 = patched_session.create_client('s3', config=client_cfg)

    with UACapHTTPStubber(client_s3) as stub_client:
        with caplog.at_level(logging.INFO):
            client_s3.list_buckets()

    # given string should be truncated to 50 characters
    uafields = stub_client.captured_ua_string.split(' ')
    assert 'app/1234-' in uafields


def test_user_agent_has_registered_feature_id(patched_session):
    client_s3 = patched_session.create_client('s3')
    with UACapHTTPStubber(client_s3) as stub_client:
        paginator = client_s3.get_paginator('list_buckets')
        # The `paginate()` method registers `'PAGINATOR': 'C'`
        for _ in paginator.paginate():
            pass
    uafields = stub_client.captured_ua_string.split(' ')
    feature_field = [field for field in uafields if field.startswith('m/')][0]
    feature_list = feature_field[2:].split(',')
    assert 'C' in feature_list


def test_registered_feature_ids_dont_bleed_between_requests(patched_session):
    client_s3 = patched_session.create_client('s3')
    with UACapHTTPStubber(client_s3) as stub_client:
        waiter = client_s3.get_waiter('bucket_exists')
        # The `wait()` method registers `'WAITER': 'B'`
        waiter.wait(Bucket='mybucket')
    uafields = stub_client.captured_ua_string.split(' ')
    feature_field = [field for field in uafields if field.startswith('m/')][0]
    feature_list = feature_field[2:].split(',')
    assert 'B' in feature_list

    with UACapHTTPStubber(client_s3) as stub_client:
        paginator = client_s3.get_paginator('list_buckets')
        # The `paginate()` method registers `'PAGINATOR': 'C'`
        for _ in paginator.paginate():
            pass
    uafields = stub_client.captured_ua_string.split(' ')
    feature_field = [field for field in uafields if field.startswith('m/')][0]
    feature_list = feature_field[2:].split(',')
    assert 'C' in feature_list
    assert 'B' not in feature_list


def test_registered_feature_ids_dont_bleed_across_threads(patched_session):
    client_s3 = patched_session.create_client('s3')
    # The client stubber isn't thread-safe because it mutates the client's
    # event system. This boolean is a workaround that ensures the paginator
    # worker's thread spawns at the same time, but does not actually execute
    # its job until the waiter thread finishes first and resets client state.
    waiter_done = False

    def wait(client, features):
        with UACapHTTPStubber(client) as stub_client:
            waiter = client.get_waiter('bucket_exists')
            # The `wait()` method registers `'WAITER': 'B'`
            waiter.wait(Bucket='mybucket')
        uafields = stub_client.captured_ua_string.split(' ')
        feature_field = [
            field for field in uafields if field.startswith('m/')
        ][0]
        features.extend(feature_field[2:].split(','))
        nonlocal waiter_done
        waiter_done = True

    def paginate(client, features):
        nonlocal waiter_done
        while not waiter_done:
            time.sleep(0.5)
        with UACapHTTPStubber(client) as stub_client:
            paginator = client.get_paginator('list_buckets')
            # The `paginate()` method registers `'PAGINATOR': 'C'`
            for _ in paginator.paginate():
                pass
        uafields = stub_client.captured_ua_string.split(' ')
        feature_field = [
            field for field in uafields if field.startswith('m/')
        ][0]
        features.extend(feature_field[2:].split(','))

    waiter_features = []
    paginator_features = []
    with futures.ThreadPoolExecutor(max_workers=2) as executor:
        waiter_future = executor.submit(wait, client_s3, waiter_features)
        paginator_future = executor.submit(
            paginate, client_s3, paginator_features
        )
        waiter_future.result()
        paginator_future.result()
    assert 'B' in waiter_features
    assert 'C' not in waiter_features
    assert 'C' in paginator_features
    assert 'B' not in paginator_features


def test_awscli_v2_user_agent(patched_session):
    # emulate behavior from awscli.clidriver._set_user_agent_for_session
    patched_session.user_agent_name = 'aws-cli'
    patched_session.user_agent_version = '2.2.2'
    patched_session.user_agent_extra = 'md/installer#source'
    # awscli.clidriver.AWSCLIEntrypoint._run_driver
    patched_session.user_agent_extra += ' md/prompt#off'
    # from awscli.clidriver.ServiceOperation._add_customization_to_user_agent
    patched_session.user_agent_extra += ' md/command#service-name.op-name'

    client_s3 = patched_session.create_client('s3')
    with UACapHTTPStubber(client_s3) as stub_client:
        client_s3.list_buckets()
    # The user agent string should start with "aws-cli/1.1.1" from the setting
    # above, followed by Botocore's version info as metadata ("md/...").
    assert stub_client.captured_ua_string.startswith(
        f'aws-cli/2.2.2 '
    )
    assert stub_client.captured_ua_string.endswith(
        ' md/installer#source md/prompt#off md/command#service-name.op-name'
    )
    # The regular User-Agent header components for platform, language, ...
    # should also be present:
    assert ' ua/2.1 ' in stub_client.captured_ua_string
    assert ' os/' in stub_client.captured_ua_string
    assert ' lang/' in stub_client.captured_ua_string
    assert ' cfg/' in stub_client.captured_ua_string
