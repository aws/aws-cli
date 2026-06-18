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
import os
import shutil
import tempfile

from s3transfer.bandwidth import (
    BandwidthLimitedStream,
    BandwidthLimiter,
    BandwidthRateTracker,
    ConsumptionScheduler,
    LeakyBucket,
    RequestExceededException,
    RequestToken,
    TimeUtils,
)
from s3transfer.futures import TransferCoordinator
from tests import mock, unittest


class FixedIncrementalTickTimeUtils(TimeUtils):
    def __init__(self, seconds_per_tick=1.0):
        self._count = 0
        self._seconds_per_tick = seconds_per_tick

    def time(self):
        current_count = self._count
        self._count += self._seconds_per_tick
        return current_count


class TestTimeUtils(unittest.TestCase):
    @mock.patch('time.time')
    def test_time(self, mock_time):
        mock_return_val = 1
        mock_time.return_value = mock_return_val
        time_utils = TimeUtils()
        self.assertEqual(time_utils.time(), mock_return_val)

    @mock.patch('time.sleep')
    def test_sleep(self, mock_sleep):
        time_utils = TimeUtils()
        time_utils.sleep(1)
        self.assertEqual(mock_sleep.call_args_list, [mock.call(1)])


class BaseBandwidthLimitTest(unittest.TestCase):
    def setUp(self):
        self.leaky_bucket = mock.Mock(LeakyBucket)
        self.time_utils = mock.Mock(TimeUtils)
        self.tempdir = tempfile.mkdtemp()
        self.content = b'a' * 1024 * 1024
        self.filename = os.path.join(self.tempdir, 'myfile')
        with open(self.filename, 'wb') as f:
            f.write(self.content)
        self.coordinator = TransferCoordinator()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def assert_consume_calls(self, amts):
        expected_consume_args = [mock.call(amt, mock.ANY) for amt in amts]
        self.assertEqual(
            self.leaky_bucket.consume.call_args_list, expected_consume_args
        )


class TestBandwidthLimiter(BaseBandwidthLimitTest):
    def setUp(self):
        super().setUp()
        self.bandwidth_limiter = BandwidthLimiter(self.leaky_bucket)

    def test_get_bandwidth_limited_stream(self):
        with open(self.filename, 'rb') as f:
            stream = self.bandwidth_limiter.get_bandwith_limited_stream(
                f, self.coordinator
            )
            self.assertIsInstance(stream, BandwidthLimitedStream)
            self.assertEqual(stream.read(len(self.content)), self.content)
            self.assert_consume_calls(amts=[len(self.content)])

    def test_get_disabled_bandwidth_limited_stream(self):
        with open(self.filename, 'rb') as f:
            stream = self.bandwidth_limiter.get_bandwith_limited_stream(
                f, self.coordinator, enabled=False
            )
            self.assertIsInstance(stream, BandwidthLimitedStream)
            self.assertEqual(stream.read(len(self.content)), self.content)
            self.leaky_bucket.consume.assert_not_called()


class TestBandwidthLimitedStream(BaseBandwidthLimitTest):
    def setUp(self):
        super().setUp()
        self.bytes_threshold = 1

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def get_bandwidth_limited_stream(self, f):
        return BandwidthLimitedStream(
            f,
            self.leaky_bucket,
            self.coordinator,
            self.time_utils,
            self.bytes_threshold,
        )

    def assert_sleep_calls(self, amts):
        expected_sleep_args_list = [mock.call(amt) for amt in amts]
        self.assertEqual(
            self.time_utils.sleep.call_args_list, expected_sleep_args_list
        )

    def get_unique_consume_request_tokens(self):
        return {
            call_args[0][1]
            for call_args in self.leaky_bucket.consume.call_args_list
        }

    def test_read(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            data = stream.read(len(self.content))
            self.assertEqual(self.content, data)
            self.assert_consume_calls(amts=[len(self.content)])
            self.assert_sleep_calls(amts=[])

    def test_retries_on_request_exceeded(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            retry_time = 1
            amt_requested = len(self.content)
            self.leaky_bucket.consume.side_effect = [
                RequestExceededException(amt_requested, retry_time),
                len(self.content),
            ]
            data = stream.read(len(self.content))
            self.assertEqual(self.content, data)
            self.assert_consume_calls(amts=[amt_requested, amt_requested])
            self.assert_sleep_calls(amts=[retry_time])

    def test_with_transfer_coordinator_exception(self):
        self.coordinator.set_exception(ValueError())
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            with self.assertRaises(ValueError):
                stream.read(len(self.content))

    def test_read_when_bandwidth_limiting_disabled(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.disable_bandwidth_limiting()
            data = stream.read(len(self.content))
            self.assertEqual(self.content, data)
            self.assertFalse(self.leaky_bucket.consume.called)

    def test_read_toggle_disable_enable_bandwidth_limiting(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.disable_bandwidth_limiting()
            data = stream.read(1)
            self.assertEqual(self.content[:1], data)
            self.assert_consume_calls(amts=[])
            stream.enable_bandwidth_limiting()
            data = stream.read(len(self.content) - 1)
            self.assertEqual(self.content[1:], data)
            self.assert_consume_calls(amts=[len(self.content) - 1])

    def test_seek(self):
        mock_fileobj = mock.Mock()
        stream = self.get_bandwidth_limited_stream(mock_fileobj)
        stream.seek(1)
        self.assertEqual(mock_fileobj.seek.call_args_list, [mock.call(1, 0)])

    def test_tell(self):
        mock_fileobj = mock.Mock()
        stream = self.get_bandwidth_limited_stream(mock_fileobj)
        stream.tell()
        self.assertEqual(mock_fileobj.tell.call_args_list, [mock.call()])

    def test_close(self):
        mock_fileobj = mock.Mock()
        stream = self.get_bandwidth_limited_stream(mock_fileobj)
        stream.close()
        self.assertEqual(mock_fileobj.close.call_args_list, [mock.call()])

    def test_context_manager(self):
        mock_fileobj = mock.Mock()
        stream = self.get_bandwidth_limited_stream(mock_fileobj)
        with stream as stream_handle:
            self.assertIs(stream_handle, stream)
        self.assertEqual(mock_fileobj.close.call_args_list, [mock.call()])

    def test_reuses_request_token(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.read(1)
            stream.read(1)
        self.assertEqual(len(self.get_unique_consume_request_tokens()), 1)

    def test_request_tokens_unique_per_stream(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.read(1)
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.read(1)
        self.assertEqual(len(self.get_unique_consume_request_tokens()), 2)

    def test_call_consume_after_reaching_threshold(self):
        self.bytes_threshold = 2
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            self.assertEqual(stream.read(1), self.content[:1])
            self.assert_consume_calls(amts=[])
            self.assertEqual(stream.read(1), self.content[1:2])
            self.assert_consume_calls(amts=[2])

    def test_resets_after_reaching_threshold(self):
        self.bytes_threshold = 2
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            self.assertEqual(stream.read(2), self.content[:2])
            self.assert_consume_calls(amts=[2])
            self.assertEqual(stream.read(1), self.content[2:3])
            self.assert_consume_calls(amts=[2])

    def test_pending_bytes_seen_on_close(self):
        self.bytes_threshold = 2
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            self.assertEqual(stream.read(1), self.content[:1])
            self.assert_consume_calls(amts=[])
            stream.close()
            self.assert_consume_calls(amts=[1])

    def test_no_bytes_remaining_on(self):
        self.bytes_threshold = 2
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            self.assertEqual(stream.read(2), self.content[:2])
            self.assert_consume_calls(amts=[2])
            stream.close()
            # There should have been no more consume() calls made
            # as all bytes have been accounted for in the previous
            # consume() call.
            self.assert_consume_calls(amts=[2])

    def test_disable_bandwidth_limiting_with_pending_bytes_seen_on_close(self):
        self.bytes_threshold = 2
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            self.assertEqual(stream.read(1), self.content[:1])
            self.assert_consume_calls(amts=[])
            stream.disable_bandwidth_limiting()
            stream.close()
            self.assert_consume_calls(amts=[])

    def test_signal_transferring(self):
        with open(self.filename, 'rb') as f:
            stream = self.get_bandwidth_limited_stream(f)
            stream.signal_not_transferring()
            data = stream.read(1)
            self.assertEqual(self.content[:1], data)
            self.assert_consume_calls(amts=[])
            stream.signal_transferring()
            data = stream.read(len(self.content) - 1)
            self.assertEqual(self.content[1:], data)
            self.assert_consume_calls(amts=[len(self.content) - 1])


class TestLeakyBucket(unittest.TestCase):
    def setUp(self):
        self.max_rate = 1
        self.time_now = 1.0
        self.time_utils = mock.Mock(TimeUtils)
        self.time_utils.time.return_value = self.time_now
        self.scheduler = mock.Mock(ConsumptionScheduler)
        self.scheduler.is_scheduled.return_value = False
        self.rate_tracker = mock.Mock(BandwidthRateTracker)
        self.leaky_bucket = LeakyBucket(
            self.max_rate, self.time_utils, self.rate_tracker, self.scheduler
        )

    def set_projected_rate(self, rate):
        self.rate_tracker.get_projected_rate.return_value = rate

    def set_retry_time(self, retry_time):
        self.scheduler.schedule_consumption.return_value = retry_time

    def assert_recorded_consumed_amt(self, expected_amt):
        self.assertEqual(
            self.rate_tracker.record_consumption_rate.call_args,
            mock.call(expected_amt, self.time_utils.time.return_value),
        )

    def assert_was_scheduled(self, amt, token):
        self.assertEqual(
            self.scheduler.schedule_consumption.call_args,
            mock.call(amt, token, amt / (self.max_rate)),
        )

    def assert_nothing_scheduled(self):
        self.assertFalse(self.scheduler.schedule_consumption.called)

    def assert_processed_request_token(self, request_token):
        self.assertEqual(
            self.scheduler.process_scheduled_consumption.call_args,
            mock.call(request_token),
        )

    def test_consume_under_max_rate(self):
        amt = 1
        self.set_projected_rate(self.max_rate / 2)
        self.assertEqual(self.leaky_bucket.consume(amt, RequestToken()), amt)
        self.assert_recorded_consumed_amt(amt)
        self.assert_nothing_scheduled()

    def test_consume_at_max_rate(self):
        amt = 1
        self.set_projected_rate(self.max_rate)
        self.assertEqual(self.leaky_bucket.consume(amt, RequestToken()), amt)
        self.assert_recorded_consumed_amt(amt)
        self.assert_nothing_scheduled()

    def test_consume_over_max_rate(self):
        amt = 1
        retry_time = 2.0
        self.set_projected_rate(self.max_rate + 1)
        self.set_retry_time(retry_time)
        request_token = RequestToken()
        try:
            self.leaky_bucket.consume(amt, request_token)
            self.fail('A RequestExceededException should have been thrown')
        except RequestExceededException as e:
            self.assertEqual(e.requested_amt, amt)
            self.assertEqual(e.retry_time, retry_time)
        self.assert_was_scheduled(amt, request_token)

    def test_consume_with_scheduled_retry(self):
        amt = 1
        self.set_projected_rate(self.max_rate + 1)
        self.scheduler.is_scheduled.return_value = True
        request_token = RequestToken()
        self.assertEqual(self.leaky_bucket.consume(amt, request_token), amt)
        # Nothing new should have been scheduled but the request token
        # should have been processed.
        self.assert_nothing_scheduled()
        self.assert_processed_request_token(request_token)


class TestConsumptionScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = ConsumptionScheduler()

    def test_schedule_consumption(self):
        token = RequestToken()
        consume_time = 5
        actual_wait_time = self.scheduler.schedule_consumption(
            1, token, consume_time
        )
        self.assertEqual(consume_time, actual_wait_time)

    def test_schedule_consumption_for_multiple_requests(self):
        token = RequestToken()
        consume_time = 5
        actual_wait_time = self.scheduler.schedule_consumption(
            1, token, consume_time
        )
        self.assertEqual(consume_time, actual_wait_time)

        other_consume_time = 3
        other_token = RequestToken()
        next_wait_time = self.scheduler.schedule_consumption(
            1, other_token, other_consume_time
        )

        # This wait time should be the previous time plus its desired
        # wait time
        self.assertEqual(next_wait_time, consume_time + other_consume_time)

    def test_is_scheduled(self):
        token = RequestToken()
        consume_time = 5
        self.scheduler.schedule_consumption(1, token, consume_time)
        self.assertTrue(self.scheduler.is_scheduled(token))

    def test_is_not_scheduled(self):
        self.assertFalse(self.scheduler.is_scheduled(RequestToken()))

    def test_process_scheduled_consumption(self):
        token = RequestToken()
        consume_time = 5
        self.scheduler.schedule_consumption(1, token, consume_time)
        self.scheduler.process_scheduled_consumption(token)
        self.assertFalse(self.scheduler.is_scheduled(token))
        different_time = 7
        # The previous consume time should have no affect on the next wait tim
        # as it has been completed.
        self.assertEqual(
            self.scheduler.schedule_consumption(1, token, different_time),
            different_time,
        )


class TestBandwidthRateTracker(unittest.TestCase):
    def setUp(self):
        self.alpha = 0.8
        self.rate_tracker = BandwidthRateTracker(self.alpha)

    def test_current_rate_at_initilizations(self):
        self.assertEqual(self.rate_tracker.current_rate, 0.0)

    def test_current_rate_after_one_recorded_point(self):
        self.rate_tracker.record_consumption_rate(1, 1)
        # There is no last time point to do a diff against so return a
        # current rate of 0.0
        self.assertEqual(self.rate_tracker.current_rate, 0.0)

    def test_current_rate(self):
        self.rate_tracker.record_consumption_rate(1, 1)
        self.rate_tracker.record_consumption_rate(1, 2)
        self.rate_tracker.record_consumption_rate(1, 3)
        self.assertEqual(self.rate_tracker.current_rate, 0.96)

    def test_get_projected_rate_at_initilizations(self):
        self.assertEqual(self.rate_tracker.get_projected_rate(1, 1), 0.0)

    def test_get_projected_rate(self):
        self.rate_tracker.record_consumption_rate(1, 1)
        self.rate_tracker.record_consumption_rate(1, 2)
        projected_rate = self.rate_tracker.get_projected_rate(1, 3)
        self.assertEqual(projected_rate, 0.96)
        self.rate_tracker.record_consumption_rate(1, 3)
        self.assertEqual(self.rate_tracker.current_rate, projected_rate)

    def test_get_projected_rate_for_same_timestamp(self):
        self.rate_tracker.record_consumption_rate(1, 1)
        self.assertEqual(
            self.rate_tracker.get_projected_rate(1, 1), float('inf')
        )
