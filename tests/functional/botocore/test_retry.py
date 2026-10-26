# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import contextlib
import datetime
import json

import botocore.endpoint
from botocore.config import Config
from botocore.exceptions import ClientError

from tests import BaseSessionTest, ClientHTTPStubber, mock
from tests.functional.botocore.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)

RETRY_MODES = ('standard', 'adaptive')


class BaseRetryTest(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = 'us-west-2'
        self.sleep_patch = mock.patch('time.sleep')
        self.sleep_patch.start()

    def tearDown(self):
        super().tearDown()
        self.sleep_patch.stop()

    @contextlib.contextmanager
    def assert_will_retry_n_times(
        self, client, num_retries, status=500, body=b'{}'
    ):
        num_responses = num_retries + 1
        if not isinstance(body, bytes):
            body = json.dumps(body).encode('utf-8')
        with ClientHTTPStubber(client) as http_stubber:
            for _ in range(num_responses):
                http_stubber.add_response(status=status, body=body)
            with self.assertRaisesRegex(
                ClientError, f'reached max retries: {num_retries}'
            ):
                yield
            self.assertEqual(len(http_stubber.requests), num_responses)

    def _get_feature_id_lists_from_retries(self, client):
        with ClientHTTPStubber(client) as http_stubber:
            # Add two failed responses followed by a success
            http_stubber.add_response(status=502, body=b'{}')
            http_stubber.add_response(status=502, body=b'{}')
            http_stubber.add_response(status=200, body=b'{}')
            client.list_tables()
        ua_strings = get_captured_ua_strings(http_stubber)
        return [
            parse_registered_feature_ids(ua_string) for ua_string in ua_strings
        ]

    def create_client_with_retry_config(
        self, service, retry_mode='standard', max_attempts=None
    ):
        retries = {'mode': retry_mode}
        if max_attempts is not None:
            retries['max_attempts'] = max_attempts
        client = self.session.create_client(
            service, self.region, config=Config(retries=retries)
        )
        return client

    def test_can_override_only_max_attempts(self):
        client = self.session.create_client(
            'dynamodb', self.region, config=Config(retries={'max_attempts': 2})
        )
        with self.assert_will_retry_n_times(client, 1):
            client.list_tables()

    def test_do_not_attempt_retries(self):
        client = self.create_client_with_retry_config(
            'dynamodb', max_attempts=1
        )
        with self.assert_will_retry_n_times(client, 0):
            client.list_tables()

    def test_setting_max_attempts_does_not_set_for_other_clients(self):
        # Make one client with max attempts configured.
        self.create_client_with_retry_config('dynamodb', max_attempts=1)

        # Make another client that has no custom retry configured.
        client = self.session.create_client('codecommit', self.region)
        # It should use the default max retries, which should be two retries
        # for this service.
        with self.assert_will_retry_n_times(client, 2):
            client.list_repositories()

    def test_set_max_attempts_on_session(self):
        self.session.set_default_client_config(
            Config(retries={'max_attempts': 2})
        )
        # Max attempts should be inherited from the session.
        client = self.session.create_client('codecommit', self.region)
        with self.assert_will_retry_n_times(client, 1):
            client.list_repositories()

    def test_can_clobber_max_attempts_on_session(self):
        self.session.set_default_client_config(
            Config(retries={'max_attempts': 5})
        )
        # Max attempts should override the session's configured max attempts.
        client = self.session.create_client(
            'codecommit',
            self.region,
            config=Config(retries={'max_attempts': 3}),
        )
        with self.assert_will_retry_n_times(client, 2):
            client.list_repositories()

    def test_standard_mode_has_default_3_attempts(self):
        client = self.create_client_with_retry_config(
            'codecommit', retry_mode='standard'
        )
        with self.assert_will_retry_n_times(client, 2):
            client.list_repositories()

    def test_standard_mode_dynamodb_has_default_4_attempts(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        with self.assert_will_retry_n_times(client, 3):
            client.list_tables()

    def test_standard_mode_can_configure_max_attempts(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard', max_attempts=5
        )
        with self.assert_will_retry_n_times(client, 4):
            client.list_tables()

    def test_no_retry_needed_standard_mode(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=200, body=b'{}')
            client.list_tables()

    def test_standard_mode_retry_throttling_error(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        error_body = {"__type": "ThrottlingException", "message": "Error"}
        with self.assert_will_retry_n_times(
            client, 3, status=400, body=error_body
        ):
            client.list_tables()

    def test_standard_mode_retry_transient_error(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        with self.assert_will_retry_n_times(client, 3, status=502):
            client.list_tables()

    def test_default_mode_retries_429_with_empty_body(self):
        # A 429 with an empty body gets the error code "429", which
        # matches neither the throttling list nor the model, so the
        # status code is used.
        client = self.session.create_client('codecommit', self.region)
        with self.assert_will_retry_n_times(client, 2, status=429, body=b''):
            client.list_repositories()

    def test_standard_mode_retries_429_with_unknown_error_code(self):
        client = self.create_client_with_retry_config(
            'codecommit', retry_mode='standard'
        )
        error_body = {"__type": "NotAThrottlingError", "message": "Error"}
        with self.assert_will_retry_n_times(
            client, 2, status=429, body=error_body
        ):
            client.list_repositories()

    def test_adaptive_mode_retries_429_with_empty_body(self):
        client = self.create_client_with_retry_config(
            'codecommit', retry_mode='adaptive'
        )
        with self.assert_will_retry_n_times(client, 2, status=429, body=b''):
            client.list_repositories()

    def test_standard_mode_does_not_retry_modeled_error_on_429(self):
        # InvalidOrderException is modeled on ListRepositories without a
        # retryable trait, so the model wins over the 429 status code.
        client = self.create_client_with_retry_config(
            'codecommit', retry_mode='standard'
        )
        error_body = {"__type": "InvalidOrderException", "message": "Error"}
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(
                status=429, body=json.dumps(error_body).encode()
            )
            with self.assertRaises(ClientError):
                client.list_repositories()
            self.assertEqual(len(http_stubber.requests), 1)

    def test_can_exhaust_default_retry_quota(self):
        # Quota of 500 / 14 retry cost == 35 retry attempts (with 10 left).
        # 35 retry attempts / 3 retries per API call == 11 client calls,
        # which consumes 462 and leaves 38 in the quota.
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        for i in range(11):
            with self.assert_will_retry_n_times(client, 3, status=502):
                client.list_tables()
        # On the 12th call, the first two retries consume 28 of the
        # remaining 38. The third retry needs 14 but only 10 is left, so
        # we should see quota errors, which we can verify by looking at
        # the request metadata.
        with ClientHTTPStubber(client) as http_stubber:
            for _ in range(3):
                http_stubber.add_response(status=502, body=b'{}')
            with self.assertRaises(ClientError) as e:
                client.list_tables()
        self.assertTrue(
            e.exception.response['ResponseMetadata'].get('RetryQuotaReached')
        )

    def test_user_agent_has_standard_mode_feature_id_by_default(self):
        client = self.session.create_client('dynamodb', self.region)
        feature_lists = self._get_feature_id_lists_from_retries(client)
        # Confirm all requests register `'RETRY_MODE_STANDARD': 'E'`
        assert all('E' in feature_list for feature_list in feature_lists)

    def test_user_agent_has_standard_mode_feature_id(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='standard'
        )
        feature_lists = self._get_feature_id_lists_from_retries(client)
        # Confirm all requests register `'RETRY_MODE_STANDARD': 'E'`
        assert all('E' in feature_list for feature_list in feature_lists)

    def test_user_agent_has_adaptive_mode_feature_id(self):
        client = self.create_client_with_retry_config(
            'dynamodb', retry_mode='adaptive'
        )
        feature_lists = self._get_feature_id_lists_from_retries(client)
        # Confirm all requests register `'RETRY_MODE_ADAPTIVE': 'F'`
        assert all('F' in feature_list for feature_list in feature_lists)


class TestRetryHeader(BaseRetryTest):
    def _retry_headers_test_cases(self):
        responses = [
            [
                (500, {'Date': 'Sat, 01 Jun 2019 00:00:00 GMT'}),
                (500, {'Date': 'Sat, 01 Jun 2019 00:00:01 GMT'}),
                (200, {'Date': 'Sat, 01 Jun 2019 00:00:02 GMT'}),
            ],
            [
                (500, {'Date': 'Sat, 01 Jun 2019 00:10:03 GMT'}),
                (500, {'Date': 'Sat, 01 Jun 2019 00:10:09 GMT'}),
                (200, {'Date': 'Sat, 01 Jun 2019 00:10:15 GMT'}),
            ],
        ]

        # The first, third and seventh datetime values of each
        # utcnow_side_effects list are side_effect values for when
        # utcnow is called in SigV4 signing.
        utcnow_side_effects = [
            [
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 1, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 1, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 2, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
            ],
            [
                datetime.datetime(2020, 6, 1, 0, 0, 0, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 5, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 6, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 11, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 12, 0),
                datetime.datetime(2019, 6, 1, 0, 0, 0, 0),
            ],
        ]
        expected_headers = [
            [
                b'attempt=1',
                b'ttl=20190601T000011Z; attempt=2; max=3',
                b'ttl=20190601T000012Z; attempt=3; max=3',
            ],
            [
                b'attempt=1',
                b'ttl=20190601T001014Z; attempt=2; max=3',
                b'ttl=20190601T001020Z; attempt=3; max=3',
            ],
        ]
        test_cases = list(
            zip(responses, utcnow_side_effects, expected_headers)
        )
        return test_cases

    def _test_amz_sdk_request_header_with_test_case(
        self, responses, utcnow_side_effects, expected_headers, client_config
    ):
        datetime_patcher = mock.patch.object(
            botocore.endpoint.datetime,
            'datetime',
            mock.Mock(wraps=datetime.datetime),
        )
        mocked_datetime = datetime_patcher.start()
        mocked_datetime.utcnow.side_effect = utcnow_side_effects

        client = self.session.create_client(
            'dynamodb', self.region, config=client_config
        )
        with ClientHTTPStubber(client) as http_stubber:
            for response in responses:
                http_stubber.add_response(
                    headers=response[1], status=response[0], body=b'{}'
                )
            client.list_tables()
            amz_sdk_request_headers = [
                request.headers['amz-sdk-request']
                for request in http_stubber.requests
            ]
            self.assertListEqual(amz_sdk_request_headers, expected_headers)
        datetime_patcher.stop()

    def test_amz_sdk_request_header(self):
        test_cases = self._retry_headers_test_cases()
        for retry_mode in RETRY_MODES:
            retries_config = {'mode': retry_mode, 'max_attempts': 3}
            client_config = Config(read_timeout=10, retries=retries_config)
            for test_case in test_cases:
                self._test_amz_sdk_request_header_with_test_case(
                    *test_case, client_config=client_config
                )

    def test_amz_sdk_invocation_id_header_persists(self):
        for retry_mode in RETRY_MODES:
            client_config = Config(retries={'mode': retry_mode})
            client = self.session.create_client(
                'dynamodb', self.region, config=client_config
            )
            num_retries = 2
            with ClientHTTPStubber(client) as http_stubber:
                for _ in range(num_retries):
                    http_stubber.add_response(status=500)
                http_stubber.add_response(status=200)
                client.list_tables()
                amz_sdk_invocation_id_headers = [
                    request.headers['amz-sdk-invocation-id']
                    for request in http_stubber.requests
                ]
                self.assertEqual(
                    amz_sdk_invocation_id_headers[0],
                    amz_sdk_invocation_id_headers[1],
                )
                self.assertEqual(
                    amz_sdk_invocation_id_headers[1],
                    amz_sdk_invocation_id_headers[2],
                )

    def test_amz_sdk_invocation_id_header_unique_per_invocation(self):
        client = self.session.create_client('dynamodb', self.region)
        num_of_invocations = 2
        with ClientHTTPStubber(client) as http_stubber:
            for _ in range(num_of_invocations):
                http_stubber.add_response(status=500)
                http_stubber.add_response(status=200)
                client.list_tables()
            amz_sdk_invocation_id_headers = [
                request.headers['amz-sdk-invocation-id']
                for request in http_stubber.requests
            ]
            self.assertEqual(
                amz_sdk_invocation_id_headers[0],
                amz_sdk_invocation_id_headers[1],
            )
            self.assertEqual(
                amz_sdk_invocation_id_headers[2],
                amz_sdk_invocation_id_headers[3],
            )
            self.assertNotEqual(
                amz_sdk_invocation_id_headers[0],
                amz_sdk_invocation_id_headers[2],
            )
