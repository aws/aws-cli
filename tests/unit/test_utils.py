# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import signal
import platform
import subprocess
import json
import os

import botocore
import botocore.session as session
from botocore.exceptions import ConnectionClosedError
from awscli.testutils import unittest, skip_if_windows, mock
from awscli.utils import (split_on_commas, ignore_ctrl_c,
                          find_service_and_method_in_event_name,
                          OutputStreamFactory)
from awscli.utils import InstanceMetadataRegionFetcher
from awscli.utils import IMDSRegionProvider
from tests import RawResponse


class TestCSVSplit(unittest.TestCase):

    def test_normal_csv_split(self):
        self.assertEqual(split_on_commas('foo,bar,baz'),
                         ['foo', 'bar', 'baz'])

    def test_quote_split(self):
        self.assertEqual(split_on_commas('foo,"bar",baz'),
                         ['foo', 'bar', 'baz'])

    def test_inner_quote_split(self):
        self.assertEqual(split_on_commas('foo,bar="1,2,3",baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_single_quote(self):
        self.assertEqual(split_on_commas("foo,bar='1,2,3',baz"),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_mixing_double_single_quotes(self):
        self.assertEqual(split_on_commas("""foo,bar="1,'2',3",baz"""),
                         ['foo', "bar=1,'2',3", 'baz'])

    def test_mixing_double_single_quotes_before_first_comma(self):
        self.assertEqual(split_on_commas("""foo,bar="1','2',3",baz"""),
                         ['foo', "bar=1','2',3", 'baz'])

    def test_inner_quote_split_with_equals(self):
        self.assertEqual(split_on_commas('foo,bar="Foo:80/bar?a=b",baz'),
                         ['foo', 'bar=Foo:80/bar?a=b', 'baz'])

    def test_single_quoted_inner_value_with_no_commas(self):
        self.assertEqual(split_on_commas("foo,bar='BAR',baz"),
                         ['foo', 'bar=BAR', 'baz'])

    def test_escape_quotes(self):
        self.assertEqual(split_on_commas('foo,bar=1\,2\,3,baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_no_commas(self):
        self.assertEqual(split_on_commas('foo'), ['foo'])

    def test_trailing_commas(self):
        self.assertEqual(split_on_commas('foo,'), ['foo', ''])

    def test_escape_backslash(self):
        self.assertEqual(split_on_commas('foo,bar\\\\,baz\\\\,qux'),
                         ['foo', 'bar\\', 'baz\\', 'qux'])

    def test_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar=["a=b",\'2\',c=d],baz'),
                         ['foo', 'bar=a=b,2,c=d', 'baz'])

    def test_quoted_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar="[blah]",c=d],baz'),
                         ['foo', 'bar=[blah]', 'c=d]', 'baz'])

    def test_missing_bracket(self):
        self.assertEqual(split_on_commas('foo,bar=[a,baz'),
                         ['foo', 'bar=[a', 'baz'])

    def test_missing_bracket2(self):
        self.assertEqual(split_on_commas('foo,bar=a],baz'),
                         ['foo', 'bar=a]', 'baz'])

    def test_bracket_in_middle(self):
        self.assertEqual(split_on_commas('foo,bar=a[b][c],baz'),
                         ['foo', 'bar=a[b][c]', 'baz'])

    def test_end_bracket_in_value(self):
        self.assertEqual(split_on_commas('foo,bar=[foo,*[biz]*,baz]'),
                         ['foo', 'bar=foo,*[biz]*,baz'])


@skip_if_windows("Ctrl-C not supported on windows.")
class TestIgnoreCtrlC(unittest.TestCase):
    def test_ctrl_c_is_ignored(self):
        with ignore_ctrl_c():
            # Should have the noop signal handler installed.
            self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
            # And if we actually try to sigint ourselves, an exception
            # should not propogate.
            os.kill(os.getpid(), signal.SIGINT)


class TestFindServiceAndOperationNameFromEvent(unittest.TestCase):
    def test_finds_service_and_operation_name(self):
        event_name = "foo.bar.baz"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertEqual(operation, "baz")

    def test_returns_none_if_event_is_too_short(self):
        event_name = "foo.bar"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertIs(operation, None)

        event_name = "foo"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertIs(service, None)
        self.assertIs(operation, None)


class MockProcess(object):
    @property
    def stdin(self):
        raise IOError('broken pipe')

    def communicate(self):
        pass


class TestOutputStreamFactory(unittest.TestCase):
    def setUp(self):
        self.popen = mock.Mock(subprocess.Popen)
        self.stream_factory = OutputStreamFactory(self.popen)

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_pager(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
                'args': ['mypager', '--option']
        }
        with self.stream_factory.get_pager_stream():
            mock_get_popen_pager.assert_called_with(None)
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args=['mypager', '--option'],
                    stdin=subprocess.PIPE)]
            )

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_env_configured_pager(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
            'args': ['mypager', '--option']
        }
        with self.stream_factory.get_pager_stream('mypager --option'):
            mock_get_popen_pager.assert_called_with('mypager --option')
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args=['mypager', '--option'],
                    stdin=subprocess.PIPE)]
            )

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_pager_using_shell(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
            'args': 'mypager --option', 'shell': True
        }
        with self.stream_factory.get_pager_stream():
            mock_get_popen_pager.assert_called_with(None)
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args='mypager --option',
                    stdin=subprocess.PIPE,
                    shell=True)]
            )

    def test_exit_of_context_manager_for_pager(self):
        with self.stream_factory.get_pager_stream():
            pass
        returned_process = self.popen.return_value
        self.assertTrue(returned_process.communicate.called)

    @mock.patch('awscli.utils.get_binary_stdout')
    def test_stdout(self, mock_binary_out):
        with self.stream_factory.get_stdout_stream():
            self.assertTrue(mock_binary_out.called)

    def test_can_silence_io_error_from_pager(self):
        self.popen.return_value = MockProcess()
        try:
            # RuntimeError is caught here since a runtime error is raised
            # when an IOError is raised before the context manager yields.
            # If we ignore it like this we will actually see the IOError.
            with self.assertRaises(RuntimeError):
                with self.stream_factory.get_pager_stream():
                    pass
        except IOError:
            self.fail('Should not raise IOError')


class TestInstanceMetadataRegionFetcher(unittest.TestCase):
    def setUp(self):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._imds_responses = []
        self._send.side_effect = self.get_imds_response
        self._region = 'us-mars-1a'

    def tearDown(self):
        self._urllib3_patch.stop()

    def add_imds_response(self, body, status_code=200):
        response = botocore.awsrequest.AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers={},
            raw=RawResponse(body)
        )
        self._imds_responses.append(response)

    def add_get_region_imds_response(self, region=None):
        if region is None:
            region = self._region
        self.add_imds_response(body=region.encode('utf-8'))

    def add_imds_connection_error(self, exception):
        self._imds_responses.append(exception)

    def get_imds_response(self, request):
        response = self._imds_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def test_disabled_by_environment(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'true'}
        fetcher = InstanceMetadataRegionFetcher(env=env)
        result = fetcher.retrieve_region()
        self.assertIsNone(result)
        self._send.assert_not_called()

    def test_disabled_by_environment_mixed_case(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'tRuE'}
        fetcher = InstanceMetadataRegionFetcher(env=env)
        result = fetcher.retrieve_region()
        self.assertIsNone(result)
        self._send.assert_not_called()

    def test_disabling_env_var_not_true(self):
        url = 'https://example.com/'
        env = {'AWS_EC2_METADATA_DISABLED': 'false'}

        self.add_get_region_imds_response()

        fetcher = InstanceMetadataRegionFetcher(base_url=url, env=env)
        result = fetcher.retrieve_region()

        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_includes_user_agent_header(self):
        user_agent = 'my-user-agent'
        self.add_get_region_imds_response()

        InstanceMetadataRegionFetcher(
            user_agent=user_agent).retrieve_region()

        headers = self._send.call_args[0][0].headers
        self.assertEqual(headers['User-Agent'], user_agent)

    def test_non_200_response_for_region_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_empty_response_for_region_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_imds_response(body=b'')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_non_200_response_is_retried(self):
        # Response for creds that has a 200 status code but has an empty
        # body should be retried.
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_http_connection_errors_is_retried(self):
        # Connection related errors should be retried
        self.add_imds_connection_error(ConnectionClosedError(endpoint_url=''))
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_empty_response_is_retried(self):
        # Response for creds that has a 200 status code but is empty.
        # This should be retried.
        self.add_imds_response(body=b'')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_exhaust_retries_on_region_request(self):
        self.add_imds_response(status_code=400, body=b'')
        result = InstanceMetadataRegionFetcher(
            num_attempts=1).retrieve_region()
        self.assertEqual(result, None)


class TestIMDSRegionProvider(unittest.TestCase):
    def assert_does_provide_expected_value(self, fetcher_region=None,
                                           expected_result=None,):
        fake_session = mock.Mock(spec=session.Session)
        fake_fetcher = mock.Mock(spec=InstanceMetadataRegionFetcher)
        fake_fetcher.retrieve_region.return_value = fetcher_region
        provider = IMDSRegionProvider(fake_session, fetcher=fake_fetcher)
        value = provider.provide()
        self.assertEqual(value, expected_result)

    def test_does_provide_region_when_present(self):
        self.assert_does_provide_expected_value(
            fetcher_region='us-mars-2',
            expected_result='us-mars-2',
        )

    def test_does_provide_none(self):
        self.assert_does_provide_expected_value(
            fetcher_region=None,
            expected_result=None,
        )
