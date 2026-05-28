"""Temporary test suite for new updated retry behavior.

These tests validate the updated retry behavior for standard retries,
which is currently gated behind an internal flag and not yet available
to external users. Once the changes are validated internally and released
publicly, these tests will replace the corresponding tests in
test_standard.py and this file will be removed.
"""

from collections import Counter

import pytest
from botocore import configprovider
from botocore.awsrequest import AWSResponse
from botocore.exceptions import ReadTimeoutError
from botocore.retries import quota, standard

from tests import BaseEnvVar, mock, unittest


@mock.patch('botocore.retries.standard.NEW_RETRIES_ENABLED', True)
class TestExponentialBackoff(unittest.TestCase):
    def setUp(self):
        self.random = lambda: 1
        self.backoff = standard.ExponentialBackoff(
            max_backoff=20, random=self.random
        )

    def test_range_of_exponential_backoff(self):
        backoffs = [
            self.backoff.delay_amount(standard.RetryContext(attempt_number=i))
            for i in range(1, 12)
        ]
        # Note that we're capped at 20 which is our max backoff.
        # Cap kicks in at attempt 10
        self.assertEqual(
            backoffs, [0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 20, 20]
        )

    def test_exponential_backoff_with_jitter(self):
        backoff = standard.ExponentialBackoff()
        backoffs = [
            backoff.delay_amount(standard.RetryContext(attempt_number=3))
            for i in range(10)
        ]
        # For attempt number 3, we should have a max value of 0.2 (0.05 * 2 ^ 2),
        # so we can assert all the backoff values are within that range.
        # 0.05 is the default non-throttling scale
        for x in backoffs:
            self.assertTrue(0 <= x <= 0.2)

    def test_uniform_rand_dist_on_max_attempts(self):
        backoff = standard.ExponentialBackoff()
        num_datapoints = 10_000
        backoffs = [
            backoff.delay_amount(standard.RetryContext(attempt_number=10))
            for i in range(num_datapoints)
        ]
        self._assert_looks_like_uniform_distribution(backoffs)

    def _assert_looks_like_uniform_distribution(self, backoffs):
        histogram = Counter(int(el) for el in backoffs)
        expected_value = len(backoffs) / len(histogram)
        # This is an arbitrarily chosen tolerance, but we're being fairly
        # lenient here and giving a 20% tolerance.  We're only interested
        # in cases where it's obviously broken and not a uniform distribution.
        tolerance = 0.20
        low = expected_value - (expected_value * tolerance)
        high = expected_value + (expected_value * tolerance)
        out_of_range = [
            str(i) for i in histogram.values() if not low <= i <= high
        ]
        if out_of_range:
            raise AssertionError(
                "Backoff values outside of uniform distribution range "
                f"({low} - {high}): {', '.join(out_of_range)}"
            )


@mock.patch('botocore.retries.standard.NEW_RETRIES_ENABLED', True)
class TestRetryQuotaChecker(unittest.TestCase):
    def setUp(self):
        self.quota = quota.RetryQuota(500)
        self.throttling_detector = standard.ThrottlingErrorDetector(
            standard.RetryEventAdapter()
        )
        self.quota_checker = standard.RetryQuotaChecker(
            self.quota, self.throttling_detector
        )
        self.request_context = {}

    def create_context(
        self,
        is_timeout_error=False,
        status_code=200,
        is_throttling_error=False,
    ):
        caught_exception = None
        parsed_response = {}
        if is_timeout_error:
            caught_exception = ReadTimeoutError(endpoint_url='https://foo')
        if is_throttling_error:
            status_code = 400
            parsed_response = {'Error': {'Code': 'Throttling'}}
        http_response = AWSResponse(
            status_code=status_code, raw=None, headers={}, url='https://foo/'
        )
        context = standard.RetryContext(
            attempt_number=1,
            request_context=self.request_context,
            caught_exception=caught_exception,
            http_response=http_response,
            parsed_response=parsed_response,
        )
        return context

    def test_can_acquire_quota_for_throttling_error(self):
        self.assertTrue(
            self.quota_checker.acquire_retry_quota(
                self.create_context(is_throttling_error=True)
            )
        )
        self.assertEqual(self.request_context['retry_quota_capacity'], 5)

    def test_can_acquire_quota_non_timeout_error(self):
        self.assertTrue(
            self.quota_checker.acquire_retry_quota(self.create_context())
        )
        self.assertEqual(self.request_context['retry_quota_capacity'], 14)

    def test_can_acquire_quota_for_timeout_error(self):
        self.assertTrue(
            self.quota_checker.acquire_retry_quota(
                self.create_context(is_timeout_error=True)
            )
        )
        self.assertEqual(self.request_context['retry_quota_capacity'], 14)

    def test_can_release_quota_based_on_context_value_on_success(self):
        context = self.create_context()
        # This is where we had to retry the request but eventually
        # succeeded.
        http_response = self.create_context(status_code=200).http_response
        self.assertTrue(self.quota_checker.acquire_retry_quota(context))
        self.assertEqual(self.quota.available_capacity, 486)
        self.quota_checker.release_retry_quota(
            context.request_context, http_response=http_response
        )
        self.assertEqual(self.quota.available_capacity, 500)

    def test_can_release_quota_when_succeed_after_throttling_error(self):
        context = self.create_context(is_throttling_error=True)
        http_response = self.create_context(status_code=200).http_response
        self.assertTrue(self.quota_checker.acquire_retry_quota(context))
        self.assertEqual(self.quota.available_capacity, 495)
        self.quota_checker.release_retry_quota(
            context.request_context, http_response=http_response
        )
        self.assertEqual(self.quota.available_capacity, 500)

    def test_dont_release_quota_if_all_retries_failed(self):
        context = self.create_context()
        # If max_attempts_reached is True, then it means we used up all
        # our retry attempts and still failed.  In this case we shouldn't
        # give any retry quota back.
        http_response = self.create_context(status_code=500).http_response
        self.assertTrue(self.quota_checker.acquire_retry_quota(context))
        self.assertEqual(self.quota.available_capacity, 486)
        self.quota_checker.release_retry_quota(
            context.request_context, http_response=http_response
        )
        self.assertEqual(self.quota.available_capacity, 486)

    def test_can_release_default_quota_if_not_in_context(self):
        context = self.create_context()
        self.assertTrue(self.quota_checker.acquire_retry_quota(context))
        self.assertEqual(self.quota.available_capacity, 486)
        # We're going to remove the quota amount from the request context.
        # This represents a successful request with no retries.
        self.request_context.pop('retry_quota_capacity')
        self.quota_checker.release_retry_quota(
            context.request_context, context.http_response
        )
        # We expect only 1 unit was released.
        self.assertEqual(self.quota.available_capacity, 487)

    def test_acquire_quota_fails(self):
        quota_checker = standard.RetryQuotaChecker(
            quota.RetryQuota(initial_capacity=14)
        )
        # The first one succeeds.
        self.assertTrue(
            quota_checker.acquire_retry_quota(self.create_context())
        )
        # But we should fail now because we're out of quota.
        self.request_context.pop('retry_quota_capacity')
        self.assertFalse(
            quota_checker.acquire_retry_quota(self.create_context())
        )
        self.assertNotIn('retry_quota_capacity', self.request_context)

    def test_quota_reached_adds_retry_metadata(self):
        quota_checker = standard.RetryQuotaChecker(
            quota.RetryQuota(initial_capacity=0)
        )
        context = self.create_context()
        self.assertFalse(quota_checker.acquire_retry_quota(context))
        self.assertEqual(
            context.get_retry_metadata(), {'RetryQuotaReached': True}
        )

    def test_single_failed_request_does_not_give_back_quota(self):
        context = self.create_context()
        http_response = self.create_context(status_code=400).http_response
        # First deduct some amount of the retry quota so we're not hitting
        # the upper bound.
        self.quota.acquire(50)
        self.assertEqual(self.quota.available_capacity, 450)
        self.quota_checker.release_retry_quota(
            context.request_context, http_response=http_response
        )
        self.assertEqual(self.quota.available_capacity, 450)


@mock.patch('botocore.retries.standard.NEW_RETRIES_ENABLED', True)
class TestServiceSpecificRetries(unittest.TestCase):
    def _make_retry_context(self, attempt, status_code, error_code=None):
        http_response = AWSResponse(
            status_code=status_code, raw=None, headers={}, url='https://foo/'
        )
        parsed_response = {}
        if error_code:
            parsed_response = {'Error': {'Code': error_code}}
        return standard.RetryContext(
            attempt_number=attempt,
            operation_model=mock.Mock(error_shapes=[]),
            http_response=http_response,
            parsed_response=parsed_response,
            request_context={},
        )

    def test_dynamodb_base_backoff_and_increased_retries(self):
        retry_quota_bucket = quota.RetryQuota()

        throttling_detector = standard.ThrottlingErrorDetector(
            standard.RetryEventAdapter()
        )
        retry_quota = standard.RetryQuotaChecker(
            retry_quota_bucket, throttling_detector
        )
        backoff = standard.ExponentialBackoff(
            random=lambda: 1,
            service_name='dynamodb',
            throttling_detector=throttling_detector,
        )

        retry_conditions = standard.StandardRetryConditions(max_attempts=4)

        # Attempts 1-3: retryable
        for attempt, expected_quota, expected_delay in [
            (1, 486, 0.025),
            (2, 472, 0.05),
            (3, 458, 0.1),
        ]:
            context = self._make_retry_context(
                attempt=attempt, status_code=500
            )
            self.assertTrue(retry_conditions.is_retryable(context))
            self.assertTrue(retry_quota.acquire_retry_quota(context))
            self.assertEqual(
                retry_quota_bucket.available_capacity, expected_quota
            )
            self.assertEqual(backoff.delay_amount(context), expected_delay)

        # Attempt 4: NOT retryable because max_attempts=4
        context4 = self._make_retry_context(attempt=4, status_code=500)
        self.assertFalse(retry_conditions.is_retryable(context4))
        self.assertEqual(retry_quota_bucket.available_capacity, 458)
        self.assertEqual(
            context4.get_retry_metadata(), {'MaxAttemptsReached': True}
        )

    def test_sqs_triggers_long_polling_backoff_when_token_empty(self):
        mock_sleep = mock.Mock()
        retry_policy = mock.Mock(spec=standard.RetryPolicy)
        retry_policy.should_retry.return_value = True
        retry_policy.compute_retry_delay.return_value = 0.05

        retry_quota = mock.Mock(spec=standard.RetryQuotaChecker)
        retry_quota.acquire_retry_quota.return_value = False

        handler = standard.RetryHandler(
            retry_policy=retry_policy,
            retry_event_adapter=standard.RetryEventAdapter(),
            retry_quota=retry_quota,
            service_name='sqs',
            sleep=mock_sleep,
        )

        context = self._make_retry_context(attempt=1, status_code=500)
        context.operation_model = mock.Mock()
        context.operation_model.name = 'ReceiveMessage'

        result = handler.needs_retry(
            response=(context.http_response, {}),
            attempts=1,
            caught_exception=None,
            request_dict={'context': {}},
            operation=context.operation_model,
        )

        assert result is False
        retry_quota.acquire_retry_quota.assert_called_once()
        mock_sleep.assert_called_once_with(0.05)

    def test_non_long_polling_operation_does_not_sleep_when_quota_exhausted(
        self,
    ):
        mock_sleep = mock.Mock()
        retry_policy = mock.Mock(spec=standard.RetryPolicy)
        retry_policy.should_retry.return_value = True
        retry_policy.compute_retry_delay.return_value = 0.05

        retry_quota = mock.Mock(spec=standard.RetryQuotaChecker)
        retry_quota.acquire_retry_quota.return_value = False

        handler = standard.RetryHandler(
            retry_policy=retry_policy,
            retry_event_adapter=standard.RetryEventAdapter(),
            retry_quota=retry_quota,
            service_name='sqs',
            sleep=mock_sleep,
        )

        context = self._make_retry_context(attempt=1, status_code=500)
        context.operation_model = mock.Mock()
        context.operation_model.name = 'SendMessage'

        result = handler.needs_retry(
            response=(context.http_response, {}),
            attempts=1,
            caught_exception=None,
            request_dict={'context': {}},
            operation=context.operation_model,
        )

        self.assertIsNone(result)
        mock_sleep.assert_not_called()


@mock.patch('botocore.retries.standard.NEW_RETRIES_ENABLED', True)
class TestRetryAfterHeaderInRetries:
    def setup_method(self):
        throttling_detector = standard.ThrottlingErrorDetector(
            standard.RetryEventAdapter()
        )
        self.retry_quota_bucket = quota.RetryQuota()
        self.retry_quota = standard.RetryQuotaChecker(
            self.retry_quota_bucket, throttling_detector
        )
        self.backoff = standard.ExponentialBackoff(
            random=lambda: 1,
            throttling_detector=throttling_detector,
        )

    def _make_retry_context(
        self, attempt, status_code, error_code=None, retry_after='0'
    ):
        http_response = AWSResponse(
            status_code=status_code,
            raw=None,
            headers={'x-amz-retry-after': retry_after},
            url='https://foo/',
        )
        parsed_response = {}
        if error_code:
            parsed_response = {'Error': {'Code': error_code}}
        return standard.RetryContext(
            attempt_number=attempt,
            operation_model=mock.Mock(error_shapes=[]),
            http_response=http_response,
            parsed_response=parsed_response,
            request_context={},
        )

    @pytest.mark.parametrize(
        'retry_after_header,'
        'expected_capacity_after_failure,'
        'expected_delay_amount,'
        'expected_capacity_after_success',
        [
            ('1500', 486, 1.5, 500),
            ('0', 486, 0.05, 500),
            ('10000', 486, 5.05, 500),
            ('invalid', 486, 0.05, 500),
            ('-100', 486, 0.05, 500),
        ],
    )
    def test_x_amz_retry_after_header_is_honored(
        self,
        retry_after_header,
        expected_capacity_after_failure,
        expected_delay_amount,
        expected_capacity_after_success,
    ):
        context = self._make_retry_context(
            attempt=1, status_code=500, retry_after=retry_after_header
        )

        assert self.retry_quota.acquire_retry_quota(context)
        assert (
            self.retry_quota_bucket.available_capacity
            == expected_capacity_after_failure
        )
        assert self.backoff.delay_amount(context) == expected_delay_amount

        http_success = AWSResponse(
            status_code=200, raw=None, headers={}, url='https://foo/'
        )
        self.retry_quota.release_retry_quota(
            context.request_context, http_response=http_success
        )
        assert (
            self.retry_quota_bucket.available_capacity
            == expected_capacity_after_success
        )


class TestNewRetriesEnvironmentVariable(BaseEnvVar):
    def test_env_var_true_enables_new_retries(self):
        self.environ['AWS_NEW_RETRIES_2026'] = 'true'
        self.assertTrue(configprovider._resolve_new_retries())

    def test_env_var_false_disables_new_retries(self):
        self.environ['AWS_NEW_RETRIES_2026'] = 'false'
        self.assertFalse(configprovider._resolve_new_retries())

    def test_no_env_var_uses_default(self):
        self.assertFalse(configprovider._resolve_new_retries())
