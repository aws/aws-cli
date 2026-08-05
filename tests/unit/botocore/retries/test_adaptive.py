from botocore.retries import adaptive, bucket, standard, throttling
from tests import mock, unittest


class FakeClock(bucket.Clock):
    def __init__(self, timestamp_sequences):
        self.timestamp_sequences = timestamp_sequences
        self.sleep_call_amounts = []

    def sleep(self, amount):
        self.sleep_call_amounts.append(amount)

    def current_time(self):
        return self.timestamp_sequences.pop(0)


class TestCanCreateRetryHandler(unittest.TestCase):
    def test_can_register_retry_handler(self):
        client = mock.Mock()
        limiter = adaptive.register_retry_handler(client)
        self.assertEqual(
            client.meta.events.register.call_args_list,
            [
                mock.call('before-send', limiter.on_sending_request),
                mock.call('needs-retry', limiter.on_receiving_response),
            ],
        )


class TestClientRateLimiter(unittest.TestCase):
    def setUp(self):
        self.timestamp_sequences = [0]
        self.clock = FakeClock(self.timestamp_sequences)
        self.token_bucket = mock.Mock(spec=bucket.TokenBucket)
        self.rate_adjustor = mock.Mock(spec=throttling.CubicCalculator)
        self.rate_clocker = mock.Mock(spec=adaptive.RateClocker)
        self.throttling_detector = mock.Mock(
            spec=standard.ThrottlingErrorDetector
        )

    def create_client_limiter(self):
        rate_limiter = adaptive.ClientRateLimiter(
            rate_adjustor=self.rate_adjustor,
            rate_clocker=self.rate_clocker,
            token_bucket=self.token_bucket,
            throttling_detector=self.throttling_detector,
            clock=self.clock,
        )
        return rate_limiter

    def test_bucket_bucket_acquisition_only_if_enabled(self):
        rate_limiter = self.create_client_limiter()
        rate_limiter.on_sending_request(request=mock.sentinel.request)
        self.assertFalse(self.token_bucket.acquire.called)

    def test_token_bucket_enabled_on_throttling_error(self):
        rate_limiter = self.create_client_limiter()
        self.throttling_detector.is_throttling_error.return_value = True
        self.rate_clocker.record.return_value = 21
        self.rate_adjustor.error_received.return_value = 17
        rate_limiter.on_receiving_response()
        # Now if we call on_receiving_response we should try to acquire
        # token.
        self.timestamp_sequences.append(1)
        rate_limiter.on_sending_request(request=mock.sentinel.request)
        self.assertTrue(self.token_bucket.acquire.called)

    def test_max_rate_updated_on_success_response(self):
        rate_limiter = self.create_client_limiter()
        self.throttling_detector.is_throttling_error.return_value = False
        self.rate_adjustor.success_received.return_value = 20
        self.rate_clocker.record.return_value = 21
        rate_limiter.on_receiving_response()
        self.assertEqual(self.token_bucket.max_rate, 20)

    def test_max_rate_cant_exceed_20_percent_max(self):
        rate_limiter = self.create_client_limiter()
        self.throttling_detector.is_throttling_error.return_value = False
        # So if our actual measured sending rate is 20 TPS
        self.rate_clocker.record.return_value = 20
        # But the rate adjustor is telling us to go up to 100 TPS
        self.rate_adjustor.success_received.return_value = 100

        # The most we should go up is 2.0 * 20
        rate_limiter.on_receiving_response()
        self.assertEqual(self.token_bucket.max_rate, 2.0 * 20)


class TestRateClocker(unittest.TestCase):
    def setUp(self):
        self.timestamp_sequences = [0]
        self.clock = FakeClock(self.timestamp_sequences)
        self.rate_measure = adaptive.RateClocker(self.clock)
        self.smoothing = 0.8

    def test_initial_rate_is_0(self):
        self.assertEqual(self.rate_measure.measured_rate, 0)

    def test_time_updates_if_after_bucket_range(self):
        self.timestamp_sequences.append(1)
        # This should be 1 * 0.8 + 0 * 0.2, or just 0.8
        self.assertEqual(self.rate_measure.record(), 0.8)

    def test_can_measure_constant_rate(self):
        # Timestamps of 1 every second indicate a rate of 1 TPS.
        self.timestamp_sequences.extend(range(1, 21))
        for _ in range(20):
            self.rate_measure.record()
        self.assertAlmostEqual(self.rate_measure.measured_rate, 1)

    def test_uses_smoothing_to_favor_recent_weights(self):
        self.timestamp_sequences.extend(
            [
                1,
                1.5,
                2,
                2.5,
                3,
                3.5,
                4,
                # If we now wait 10 seconds (.1 TPS),
                # our rate is somewhere between 2 TPS and .1 TPS.
                14,
            ]
        )
        for _ in range(7):
            self.rate_measure.record()
        # We should almost be at 2.0 but not quite.
        self.assertGreaterEqual(self.rate_measure.measured_rate, 1.99)
        self.assertLessEqual(self.rate_measure.measured_rate, 2.0)
        # With our last recording we now drop down between 0.1 and 2
        # depending on our smoothing factor.
        self.rate_measure.record()
        self.assertGreaterEqual(self.rate_measure.measured_rate, 0.1)
        self.assertLessEqual(self.rate_measure.measured_rate, 2.0)

    def test_noop_when_delta_t_is_0(self):
        self.timestamp_sequences.extend([1, 1, 1, 2, 3])
        for _ in range(5):
            self.rate_measure.record()
        self.assertGreaterEqual(self.rate_measure.measured_rate, 1.0)

    def test_times_are_grouped_per_time_bucket(self):
        # Using our default of 0.5 time buckets, we have:
        self.timestamp_sequences.extend(
            [
                0.1,
                0.2,
                0.3,
                0.4,
                0.49,
            ]
        )
        for _ in range(len(self.timestamp_sequences)):
            self.rate_measure.record()
        # This is showing the tradeoff we're making with measuring rates.
        # we're currently in the window from 0 <= x < 0.5, which means
        # we use the rate from the previous bucket, which is 0:
        self.assertEqual(self.rate_measure.measured_rate, 0)
        # However if we now add a new measurement that's in the next
        # time bucket  0.5 <= x < 1.0
        # we'll use the range from the previous bucket:
        self.timestamp_sequences.append(0.5)
        self.rate_measure.record()
        # And our previous bucket will be:
        # 12 * 0.8 + 0.2 * 0
        self.assertEqual(self.rate_measure.measured_rate, 12 * 0.8)
