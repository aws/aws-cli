from collections import Counter

import pytest
from botocore import model
from botocore.awsrequest import AWSResponse
from botocore.exceptions import (
    ConnectionError,
    HTTPClientError,
    ReadTimeoutError,
)
from botocore.retries import quota, standard

from tests import mock, unittest

RETRYABLE_THROTTLED_RESPONSES = [
    # From the spec under "Throttling Errors"
    # The status codes technically don't matter here, but we're adding
    # them for completeness.
    # StatusCode, ErrorCode, Retryable?
    (400, 'Throttling', True),
    (400, 'ThrottlingException', True),
    (400, 'ThrottledException', True),
    (400, 'RequestThrottledException', True),
    (400, 'TooManyRequestsException', True),
    (400, 'ProvisionedThroughputExceededException', True),
    (503, 'RequestLimitExceeded', True),
    (509, 'BandwidthLimitExceeded', True),
    (400, 'LimitExceededException', True),
    (403, 'RequestThrottled', True),
    (503, 'SlowDown', True),
    (503, 'SlowDown', True),
    (400, 'PriorRequestNotComplete', True),
    (502, 'EC2ThrottledException', True),
    # These are some negative test cases, not in the spec but we'll use
    # to verify we can detect throttled errors correctly.
    (400, 'NotAThrottlingError', False),
    (500, 'InternalServerError', False),
    # "None" here represents no parsed response we just have a plain
    # HTTP response and a 400 status code response.
    (400, None, False),
    (500, None, False),
    (200, None, False),
    # A 429 is only retryable via its status code, not its error code.
    (429, None, False),
    (429, 'NotAThrottlingError', False),
]

RETRYABLE_THROTTLING_STATUS_CODES = [
    # StatusCode, ErrorCode, Retryable?
    # "429" is the error code botocore assigns to a 429 with no parsed
    # error code, e.g. an empty body.
    (429, '429', True),
    (429, None, True),
    (429, 'NotAThrottlingError', True),
    (429, 'ThrottlingException', True),
    # Negative cases: the status code is all that matters here.
    (400, 'Throttling', False),
    (400, None, False),
    (500, None, False),
    (503, 'SlowDown', False),
    (None, ConnectionError(error='unknown'), False),
]

RETRYABLE_TRANSIENT_ERRORS = [
    # StatusCode, Error, Retryable?
    (400, 'RequestTimeout', True),
    (400, 'RequestTimeoutException', True),
    (400, 'PriorRequestNotComplete', True),
    # "Any HTTP response with an HTTP status code of 500, 502, 503, or 504".
    (500, None, True),
    (502, None, True),
    (503, None, True),
    (504, None, True),
    # We'll also add a few errors with an explicit error code to verify
    # that the code doesn't matter.
    (500, 'InternalServiceError', True),
    (502, 'BadError', True),
    # These are botocore specific errors that correspond to
    # "Any IO (socket) level error where we are unable to read an HTTP
    # response.
    (None, ConnectionError(error='unknown'), True),
    (None, HTTPClientError(error='unknown'), True),
    # Negative cases
    (200, None, False),
    # This is a throttling error not a transient error
    (400, 'Throttling', False),
    (400, None, False),
]


# These tests are intended to be paired with the
# SERVICE_DESCRIPTION_WITH_RETRIES definition.
RETRYABLE_MODELED_ERRORS = [
    (400, 'ModeledThrottlingError', True),
    (400, 'ModeledRetryableError', True),
    # Note this is ErrorCodeRetryable, not ModeledRetryableErrorWithCode,
    # because the shape has a error code defined for it.
    (400, 'ErrorCodeRetryable', True),
    (400, 'NonRetryableError', False),
    (None, ConnectionError(error='unknown'), False),
]


SERVICE_DESCRIPTION_WITH_RETRIES = {
    'metadata': {},
    'operations': {
        'TestOperation': {
            'name': 'TestOperation',
            'input': {'shape': 'FakeInputOutputShape'},
            'output': {'shape': 'FakeInputOutputShape'},
            'errors': [
                {'shape': 'ModeledThrottlingError'},
                {'shape': 'ModeledRetryableError'},
                {'shape': 'ModeledRetryableErrorWithCode'},
                {'shape': 'NonRetryableError'},
            ],
        }
    },
    'shapes': {
        'FakeInputOutputShape': {
            'type': 'structure',
            'members': {},
        },
        'ModeledThrottlingError': {
            'type': 'structure',
            'members': {
                'message': {
                    'shape': 'ErrorMessage',
                }
            },
            'exception': True,
            'retryable': {'throttling': True},
        },
        'ModeledRetryableError': {
            'type': 'structure',
            'members': {
                'message': {
                    'shape': 'ErrorMessage',
                }
            },
            'exception': True,
            'retryable': {},
        },
        'ModeledRetryableErrorWithCode': {
            'type': 'structure',
            'members': {
                'message': {
                    'shape': 'ErrorMessage',
                }
            },
            'error': {
                'code': 'ErrorCodeRetryable',
            },
            'exception': True,
            'retryable': {'throttling': True},
        },
        'NonRetryableError': {
            'type': 'structure',
            'members': {
                'message': {
                    'shape': 'ErrorMessage',
                }
            },
            'exception': True,
        },
    },
}


@pytest.mark.parametrize('case', RETRYABLE_TRANSIENT_ERRORS)
def test_can_detect_retryable_transient_errors(case):
    transient_checker = standard.TransientRetryableChecker()
    _verify_retryable(transient_checker, None, *case)


@pytest.mark.parametrize('case', RETRYABLE_THROTTLED_RESPONSES)
def test_can_detect_retryable_throttled_errors(case):
    throttled_checker = standard.ThrottledRetryableChecker()
    _verify_retryable(throttled_checker, None, *case)


@pytest.mark.parametrize('case', RETRYABLE_THROTTLING_STATUS_CODES)
def test_can_detect_throttling_status_codes(case):
    status_code_checker = standard.ThrottlingStatusCodeChecker()
    _verify_retryable(status_code_checker, None, *case)


@pytest.mark.parametrize(
    'case',
    [
        # The 429 status code only applies to errors the model doesn't
        # cover.  Any modeled error, retryable or not, is left to the
        # modeled retry checker.
        (429, 'NonRetryableError', False),
        (429, 'ModeledRetryableError', False),
        (429, 'ModeledThrottlingError', False),
        (429, 'ErrorCodeRetryable', False),
        (429, 'NotAModeledError', True),
        (429, '429', True),
        (429, None, True),
    ],
)
def test_throttling_status_code_checker_skips_modeled_errors(case):
    status_code_checker = standard.ThrottlingStatusCodeChecker()
    _verify_retryable(
        status_code_checker, get_operation_model_with_retries(), *case
    )


def test_throttling_status_code_checker_ignores_missing_response():
    status_code_checker = standard.ThrottlingStatusCodeChecker()
    context = standard.RetryContext(
        attempt_number=1,
        http_response=None,
        caught_exception=ConnectionError(error='unknown'),
    )
    assert not status_code_checker.is_retryable(context)


@pytest.mark.parametrize('case', RETRYABLE_MODELED_ERRORS)
def test_can_detect_modeled_retryable_errors(case):
    modeled_retry_checker = standard.ModeledRetryableChecker()
    _verify_retryable(
        modeled_retry_checker, get_operation_model_with_retries(), *case
    )


@pytest.mark.parametrize(
    'case',
    [
        case
        for case in RETRYABLE_TRANSIENT_ERRORS
        + RETRYABLE_THROTTLED_RESPONSES
        + RETRYABLE_THROTTLING_STATUS_CODES
        + RETRYABLE_MODELED_ERRORS
        if case[2]
    ],
)
def test_standard_retry_conditions(case):
    """This is verifying that the high level object used for checking
    retry conditions still handles all the individual testcases.

    It's possible that cases that are retryable for an individual checker
    aren't retryable for a different checker.  We need to filter out all
    the False cases (if case[2]).
    """
    standard_checker = standard.StandardRetryConditions()
    op_model = get_operation_model_with_retries()
    _verify_retryable(standard_checker, op_model, *case)


@pytest.mark.parametrize(
    'case',
    [
        # A modeled error without a retryable trait is not retried, even
        # when the service returns it with a 429 status code.  The model
        # takes precedence over the status code.
        (429, 'NonRetryableError', False),
        # A modeled error with a retryable trait is still retried.
        (429, 'ModeledRetryableError', True),
        (429, 'NotAModeledError', True),
    ],
)
def test_standard_retry_conditions_with_model_on_429(case):
    standard_checker = standard.StandardRetryConditions()
    op_model = get_operation_model_with_retries()
    _verify_retryable(standard_checker, op_model, *case)


def get_operation_model_with_retries():
    service = model.ServiceModel(
        SERVICE_DESCRIPTION_WITH_RETRIES, service_name='my-service'
    )
    return service.operation_model('TestOperation')


def _verify_retryable(
    checker, operation_model, status_code, error, is_retryable
):
    http_response = AWSResponse(
        status_code=status_code, raw=None, headers={}, url='https://foo/'
    )
    parsed_response = None
    caught_exception = None
    if error is not None:
        if isinstance(error, Exception):
            caught_exception = error
        else:
            parsed_response = {'Error': {'Code': error, 'Message': 'Error'}}
    context = standard.RetryContext(
        attempt_number=1,
        operation_model=operation_model,
        parsed_response=parsed_response,
        http_response=http_response,
        caught_exception=caught_exception,
    )
    assert checker.is_retryable(context) == is_retryable


def arbitrary_retry_context():
    # Used when you just need a dummy retry context that looks like
    # a failed request.
    return standard.RetryContext(
        attempt_number=1,
        operation_model=None,
        parsed_response={'Error': {'Code': 'ErrorCode', 'Message': 'message'}},
        http_response=AWSResponse(
            status_code=500, raw=None, headers={}, url='https://foo'
        ),
        caught_exception=None,
    )


def test_can_honor_max_attempts():
    checker = standard.MaxAttemptsChecker(max_attempts=3)
    context = arbitrary_retry_context()
    context.attempt_number = 1
    assert checker.is_retryable(context) is True

    context.attempt_number = 2
    assert checker.is_retryable(context) is True

    context.attempt_number = 3
    assert checker.is_retryable(context) is False


def test_max_attempts_adds_metadata_key_when_reached():
    checker = standard.MaxAttemptsChecker(max_attempts=3)
    context = arbitrary_retry_context()
    context.attempt_number = 3
    assert checker.is_retryable(context) is False
    assert context.get_retry_metadata() == {'MaxAttemptsReached': True}


def test_can_create_default_retry_handler():
    mock_client = mock.Mock()
    mock_client.meta.service_model.service_id = model.ServiceId('my-service')
    assert isinstance(
        standard.register_retry_handler(mock_client), standard.RetryHandler
    )
    call_args_list = mock_client.meta.events.register.call_args_list
    # We should have registered the retry quota to after-calls
    first_call = call_args_list[0][0]
    second_call = call_args_list[1][0]
    # Not sure if there's a way to verify the class associated with the
    # bound method matches what we expect.
    assert first_call[0] == 'after-call.my-service'
    assert second_call[0] == 'needs-retry.my-service'


class TestRetryHandler(unittest.TestCase):
    def setUp(self):
        self.retry_policy = mock.Mock(spec=standard.RetryPolicy)
        self.retry_event_adapter = mock.Mock(spec=standard.RetryEventAdapter)
        self.retry_quota = mock.Mock(spec=standard.RetryQuotaChecker)
        self.retry_handler = standard.RetryHandler(
            retry_policy=self.retry_policy,
            retry_event_adapter=self.retry_event_adapter,
            retry_quota=self.retry_quota,
        )

    def test_does_need_retry(self):
        self.retry_event_adapter.create_retry_context.return_value = (
            mock.sentinel.retry_context
        )
        self.retry_policy.should_retry.return_value = True
        self.retry_quota.acquire_retry_quota.return_value = True
        self.retry_policy.compute_retry_delay.return_value = 1

        self.assertEqual(self.retry_handler.needs_retry(fake_kwargs='foo'), 1)
        self.retry_event_adapter.create_retry_context.assert_called_with(
            fake_kwargs='foo'
        )
        self.retry_policy.should_retry.assert_called_with(
            mock.sentinel.retry_context
        )
        self.retry_quota.acquire_retry_quota.assert_called_with(
            mock.sentinel.retry_context
        )
        self.retry_policy.compute_retry_delay.assert_called_with(
            mock.sentinel.retry_context
        )

    def test_does_not_need_retry(self):
        self.retry_event_adapter.create_retry_context.return_value = (
            mock.sentinel.retry_context
        )
        self.retry_policy.should_retry.return_value = False

        self.assertIsNone(self.retry_handler.needs_retry(fake_kwargs='foo'))
        # Shouldn't consult quota if we don't have a retryable condition.
        self.assertFalse(self.retry_quota.acquire_retry_quota.called)

    def test_needs_retry_but_not_enough_quota(self):
        self.retry_event_adapter.create_retry_context.return_value = (
            mock.sentinel.retry_context
        )
        self.retry_policy.should_retry.return_value = True
        self.retry_quota.acquire_retry_quota.return_value = False

        self.assertIsNone(self.retry_handler.needs_retry(fake_kwargs='foo'))

    def test_retry_handler_adds_retry_metadata_to_response(self):
        self.retry_event_adapter.create_retry_context.return_value = (
            mock.sentinel.retry_context
        )
        self.retry_policy.should_retry.return_value = False
        self.assertIsNone(self.retry_handler.needs_retry(fake_kwargs='foo'))
        adapter = self.retry_event_adapter
        adapter.adapt_retry_response_from_context.assert_called_with(
            mock.sentinel.retry_context
        )


class TestRetryEventAdapter(unittest.TestCase):
    def setUp(self):
        self.success_response = {'ResponseMetadata': {}, 'Foo': {}}
        self.failed_response = {'ResponseMetadata': {}, 'Error': {}}
        self.http_success = AWSResponse(
            status_code=200, raw=None, headers={}, url='https://foo/'
        )
        self.http_failed = AWSResponse(
            status_code=500, raw=None, headers={}, url='https://foo/'
        )
        self.caught_exception = ConnectionError(error='unknown')

    def test_create_context_from_success_response(self):
        context = standard.RetryEventAdapter().create_retry_context(
            response=(self.http_success, self.success_response),
            attempts=1,
            caught_exception=None,
            request_dict={'context': {'foo': 'bar'}},
            operation=mock.sentinel.operation_model,
        )

        self.assertEqual(context.attempt_number, 1)
        self.assertEqual(
            context.operation_model, mock.sentinel.operation_model
        )
        self.assertEqual(context.parsed_response, self.success_response)
        self.assertEqual(context.http_response, self.http_success)
        self.assertEqual(context.caught_exception, None)
        self.assertEqual(context.request_context, {'foo': 'bar'})

    def test_create_context_from_service_error(self):
        context = standard.RetryEventAdapter().create_retry_context(
            response=(self.http_failed, self.failed_response),
            attempts=1,
            caught_exception=None,
            request_dict={'context': {'foo': 'bar'}},
            operation=mock.sentinel.operation_model,
        )
        # We already tested the other attributes in
        # test_create_context_from_success_response so we're only checking
        # the attributes relevant to this test.
        self.assertEqual(context.parsed_response, self.failed_response)
        self.assertEqual(context.http_response, self.http_failed)

    def test_create_context_from_exception(self):
        context = standard.RetryEventAdapter().create_retry_context(
            response=None,
            attempts=1,
            caught_exception=self.caught_exception,
            request_dict={'context': {'foo': 'bar'}},
            operation=mock.sentinel.operation_model,
        )
        self.assertEqual(context.parsed_response, None)
        self.assertEqual(context.http_response, None)
        self.assertEqual(context.caught_exception, self.caught_exception)

    def test_can_inject_metadata_back_to_context(self):
        adapter = standard.RetryEventAdapter()
        context = adapter.create_retry_context(
            attempts=1,
            operation=None,
            caught_exception=None,
            request_dict={'context': {}},
            response=(self.http_failed, self.failed_response),
        )
        context.add_retry_metadata(MaxAttemptsReached=True)
        adapter.adapt_retry_response_from_context(context)
        self.assertEqual(
            self.failed_response['ResponseMetadata']['MaxAttemptsReached'],
            True,
        )


class TestRetryPolicy(unittest.TestCase):
    def setUp(self):
        self.retry_checker = mock.Mock(spec=standard.StandardRetryConditions)
        self.retry_backoff = mock.Mock(spec=standard.ExponentialBackoff)
        self.retry_policy = standard.RetryPolicy(
            retry_checker=self.retry_checker, retry_backoff=self.retry_backoff
        )

    def test_delegates_to_retry_checker(self):
        self.retry_checker.is_retryable.return_value = True
        self.assertTrue(self.retry_policy.should_retry(mock.sentinel.context))
        self.retry_checker.is_retryable.assert_called_with(
            mock.sentinel.context
        )

    def test_delegates_to_retry_backoff(self):
        self.retry_backoff.delay_amount.return_value = 1
        self.assertEqual(
            self.retry_policy.compute_retry_delay(mock.sentinel.context), 1
        )
        self.retry_backoff.delay_amount.assert_called_with(
            mock.sentinel.context
        )


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

    def test_bare_429_uses_throttling_base_scale(self):
        backoff = standard.ExponentialBackoff(
            random=self.random,
            throttling_detector=standard.ThrottlingErrorDetector(
                standard.RetryEventAdapter()
            ),
        )
        http_response = AWSResponse(
            status_code=429, raw=None, headers={}, url='https://foo/'
        )
        context = standard.RetryContext(
            attempt_number=1, http_response=http_response, parsed_response={}
        )
        # Throttling scale is 1, non-throttling scale is 0.05.
        self.assertEqual(backoff.delay_amount(context), 1)

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

    def test_can_acquire_quota_for_bare_429(self):
        # A 429 with no throttling error code is still a throttling error.
        self.assertTrue(
            self.quota_checker.acquire_retry_quota(
                self.create_context(status_code=429)
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


class TestRetryContext(unittest.TestCase):
    def test_can_get_error_code(self):
        context = arbitrary_retry_context()
        context.parsed_response['Error']['Code'] = 'MyErrorCode'
        self.assertEqual(context.get_error_code(), 'MyErrorCode')

    def test_no_error_code_if_no_parsed_response(self):
        context = arbitrary_retry_context()
        context.parsed_response = None
        self.assertIsNone(context.get_error_code())

    def test_no_error_code_returns_none(self):
        context = arbitrary_retry_context()
        context.parsed_response = {}
        self.assertIsNone(context.get_error_code())

    def test_can_add_retry_reason(self):
        context = arbitrary_retry_context()
        context.add_retry_metadata(MaxAttemptsReached=True)
        self.assertEqual(
            context.get_retry_metadata(), {'MaxAttemptsReached': True}
        )

    def test_handles_non_error_top_level_error_key_get_error_code(self):
        response = AWSResponse(
            status_code=200,
            raw=None,
            headers={},
            url='https://foo',
        )
        # A normal response can have a top level "Error" key that doesn't map
        # to an error code and should be ignored
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=None,
            parsed_response={'Error': 'This is a 200 response body'},
            http_response=response,
            caught_exception=None,
        )
        self.assertEqual(context.get_error_code(), None)


class TestThrottlingErrorDetector(unittest.TestCase):
    def setUp(self):
        self.throttling_detector = standard.ThrottlingErrorDetector(
            standard.RetryEventAdapter()
        )

    def create_needs_retry_kwargs(self, **kwargs):
        retry_kwargs = {
            'response': None,
            'attempts': 1,
            'operation': None,
            'caught_exception': None,
            'request_dict': {'context': {}},
        }
        retry_kwargs.update(kwargs)
        return retry_kwargs

    def test_can_check_error_from_code(self):
        kwargs = self.create_needs_retry_kwargs()
        kwargs['response'] = (None, {'Error': {'Code': 'ThrottledException'}})
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))

    def test_no_throttling_error(self):
        kwargs = self.create_needs_retry_kwargs()
        kwargs['response'] = (None, {'Error': {'Code': 'RandomError'}})
        self.assertFalse(
            self.throttling_detector.is_throttling_error(**kwargs)
        )

    def test_detects_modeled_errors(self):
        kwargs = self.create_needs_retry_kwargs()
        kwargs['response'] = (
            None,
            {'Error': {'Code': 'ModeledThrottlingError'}},
        )
        kwargs['operation'] = get_operation_model_with_retries()
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))

    def create_429_kwargs(self, error_code, operation_model=None):
        http_response = AWSResponse(
            status_code=429, raw=None, headers={}, url='https://foo/'
        )
        parsed_response = {}
        if error_code is not None:
            parsed_response = {'Error': {'Code': error_code}}
        return self.create_needs_retry_kwargs(
            response=(http_response, parsed_response),
            operation=operation_model,
        )

    def test_detects_429_without_error_code(self):
        kwargs = self.create_429_kwargs(error_code=None)
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))

    def test_detects_429_with_unknown_error_code(self):
        kwargs = self.create_429_kwargs(error_code='RandomError')
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))

    def test_detects_429_with_unknown_error_code_and_model(self):
        # The error code matches none of the modeled errors, so the
        # status code decides.
        kwargs = self.create_429_kwargs(
            error_code='RandomError',
            operation_model=get_operation_model_with_retries(),
        )
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))

    def test_modeled_error_without_retryable_trait_is_not_throttling(self):
        # The model takes precedence over the 429 status code.
        kwargs = self.create_429_kwargs(
            error_code='NonRetryableError',
            operation_model=get_operation_model_with_retries(),
        )
        self.assertFalse(
            self.throttling_detector.is_throttling_error(**kwargs)
        )

    def test_modeled_retryable_trait_wins_over_429(self):
        # The model says this is a non-throttling retryable error, which
        # takes precedence over the 429 status code.
        kwargs = self.create_429_kwargs(
            error_code='ModeledRetryableError',
            operation_model=get_operation_model_with_retries(),
        )
        self.assertFalse(
            self.throttling_detector.is_throttling_error(**kwargs)
        )

    def test_modeled_throttling_trait_on_429(self):
        kwargs = self.create_429_kwargs(
            error_code='ModeledThrottlingError',
            operation_model=get_operation_model_with_retries(),
        )
        self.assertTrue(self.throttling_detector.is_throttling_error(**kwargs))


class TestModeledRetryErrorDetector(unittest.TestCase):
    def setUp(self):
        self.modeled_error = standard.ModeledRetryErrorDetector()

    def test_not_retryable(self):
        context = arbitrary_retry_context()
        self.assertIsNone(self.modeled_error.detect_error_type(context))

    def test_transient_error(self):
        context = arbitrary_retry_context()
        context.parsed_response['Error']['Code'] = 'ModeledRetryableError'
        context.operation_model = get_operation_model_with_retries()
        self.assertEqual(
            self.modeled_error.detect_error_type(context),
            self.modeled_error.TRANSIENT_ERROR,
        )

    def test_throttling_error(self):
        context = arbitrary_retry_context()
        context.parsed_response['Error']['Code'] = 'ModeledThrottlingError'
        context.operation_model = get_operation_model_with_retries()
        self.assertEqual(
            self.modeled_error.detect_error_type(context),
            self.modeled_error.THROTTLING_ERROR,
        )


class Yes(standard.BaseRetryableChecker):
    def is_retryable(self, context):
        return True


class No(standard.BaseRetryableChecker):
    def is_retryable(self, context):
        return False


class TestOrRetryChecker(unittest.TestCase):
    def test_can_match_any_checker(self):
        self.assertTrue(standard.OrRetryChecker([Yes(), No()]))
        self.assertTrue(standard.OrRetryChecker([No(), Yes()]))
        self.assertTrue(standard.OrRetryChecker([Yes(), Yes()]))

    def test_false_if_no_checkers_match(self):
        self.assertTrue(standard.OrRetryChecker([No(), No(), No()]))
