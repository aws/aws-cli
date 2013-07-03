import random
import functools
import logging
from binascii import crc32

from botocore.exceptions import ChecksumError


log = logging.getLogger(__name__)


def delay_exponential(base, growth_factor, attempts):
    """Calculate time to sleep based on exponential function.

    The format is::

        base * growth_factor ^ (attempts - 1)

    If ``base`` is set to 'rand' then a random number between
    0 and 1 will be used as the base.
    Base must be greater than 0, otherwise a ValueError will be
    raised.

    """
    if base == 'rand':
        base = random.random()
    elif base <= 0:
        raise ValueError("The 'base' param must be greater than 0, "
                         "got: %s" % base)
    time_to_sleep = base * (growth_factor ** (attempts - 1))
    return time_to_sleep


def create_exponential_delay_function(base, growth_factor):
    """Create an exponential delay function based on the attempts.

    This is used so that you only have to pass it the attempts
    parameter to calculate the delay.

    """
    return functools.partial(
        delay_exponential, base=base, growth_factor=growth_factor)


def create_retry_handler(config, operation_name=None):
    checker = create_checker_from_retry_config(
        config, operation_name=operation_name)
    action = create_retry_action_from_config(
        config, operation_name=operation_name)
    return RetryHandler(checker=checker, action=action)


def create_retry_action_from_config(config, operation_name=None):
    # The spec has the possibility of supporting per policy
    # actions, but right now, we assume this comes from the
    # default section, which means that delay functions apply
    # for every policy in the retry config (per service).
    delay_config = config['__default__']['delay']
    if delay_config['type'] == 'exponential':
        return create_exponential_delay_function(
            base=delay_config['base'],
            growth_factor=delay_config['growth_factor'])


def create_checker_from_retry_config(config, operation_name=None):
    checkers = []
    max_attempts = None
    retryable_exceptions = []
    if '__default__' in config:
        policies = config['__default__'].get('policies', [])
        max_attempts = config['__default__']['max_attempts']
        for key in policies:
            current_config = policies[key]
            checkers.append(_create_single_checker(current_config))
            retry_exception = _extract_retryable_exception(current_config)
            if retry_exception is not None:
                retryable_exceptions.append(retry_exception)
    if operation_name is not None and config.get(operation_name) is not None:
        operation_policies = config[operation_name]['policies']
        for key in operation_policies:
            checkers.append(_create_single_checker(operation_policies[key]))
            retry_exception = _extract_retryable_exception(
                operation_policies[key])
            if retry_exception is not None:
                retryable_exceptions.append(retry_exception)
    if len(checkers) == 1:
        # Don't need to use a MultiChecker
        return MaxAttemptsDecorator(checkers[0], max_attempts=max_attempts)
    else:
        multi_checker = MultiChecker(checkers)
        return MaxAttemptsDecorator(
            multi_checker, max_attempts=max_attempts,
            retryable_exceptions=tuple(retryable_exceptions))


def _create_single_checker(config):
    response = config['applies_when']['response']
    if 'service_error_code' in response:
        checker = ServiceErrorCodeChecker(
            status_code=response['http_status_code'],
            error_code=response['service_error_code'])
    elif 'http_status_code' in response:
        checker = HTTPStatusCodeChecker(
            status_code=response['http_status_code'])
    elif 'crc32body' in response:
        checker = CRC32Checker(header=response['crc32body'])
    else:
        raise ValueError("Unknown retry policy: %s" % config)
    return checker


def _extract_retryable_exception(config):
    response = config['applies_when']['response']
    if 'crc32body' in response:
        return ChecksumError


class RetryHandler(object):
    """Retry handler.

    The retry handler takes two params, ``checker`` object
    and an ``action`` object.

    The ``checker`` object must be a callable object and based on a response
    and an attempt number, determines whether or not sufficient criteria for
    a retry has been met.  If this is the case then the ``action`` object
    (which also is a callable) determines what needs to happen in the event
    of a retry.

    """

    def __init__(self, checker, action):
        self._checker = checker
        self._action = action

    def __call__(self, response, attempts, **kwargs):
        """Handler for a retry.

        Intended to be hooked up to an event handler (hence the **kwargs),
        this will process retries appropriately.

        """
        if self._checker(response, attempts):
            return self._action(attempts=attempts)


class MaxAttemptsDecorator(object):
    """Allow retries up to a maximum number of attempts.

    This will pass through calls to the decorated retry checker, provided
    that the number of attempts does not exceed max_attempts.  It will
    also catch any retryable_exceptions passed in.  Once max_attempts has
    been exceeded, then False will be returned or the retryable_exceptions
    that was previously being caught will be raised.

    """
    def __init__(self, checker, max_attempts, retryable_exceptions=None):
        self._checker = checker
        self._max_attempts = max_attempts
        self._retryable_exceptions = retryable_exceptions

    def __call__(self, response, attempt_number):
        should_retry = self._should_retry(response, attempt_number)
        if should_retry:
            if attempt_number >= self._max_attempts:
                return False
            else:
                return should_retry
        else:
            return False

    def _should_retry(self, response, attempt_number):
        if self._retryable_exceptions and \
                attempt_number < self._max_attempts:
            try:
                return self._checker(response, attempt_number)
            except self._retryable_exceptions as e:
                return True
        else:
            return self._checker(response, attempt_number)


class HTTPStatusCodeChecker(object):
    def __init__(self, status_code):
        self._status_code = status_code

    def __call__(self, response, attempt_number):
        return response[0].status_code == self._status_code


class ServiceErrorCodeChecker(object):
    def __init__(self, status_code, error_code):
        self._status_code = status_code
        self._error_code = error_code

    def __call__(self, response, attempt_number):
        if response[0].status_code == self._status_code:
            return any([e.get('Code') == self._error_code
                        for e in response[1].get('Errors', [])])
        return False


class MultiChecker(object):
    def __init__(self, checkers):
        self._checkers = checkers

    def __call__(self, response, attempt_number):
        for checker in self._checkers:
            checker_response = checker(response, attempt_number)
            if checker_response:
                return checker_response
        return False


class CRC32Checker(object):
    def __init__(self, header):
        # The header where the expected crc32 is located.
        self._header_name = header

    def __call__(self, response, attempt_number):
        http_response = response[0]
        expected_crc = http_response.headers.get(self._header_name)
        if expected_crc is None:
            log.debug("crc32 check skipped, the %s header is not "
                      "in the http response.", self._header_name)
        else:
            actual_crc32 = crc32(response[0].content) & 0xffffffff
            if not actual_crc32 == int(expected_crc):
                log.debug("crc32 check failed, expected != actual: "
                          "%s != %s", int(expected_crc), actual_crc32)
                raise ChecksumError(checksum_type='crc32',
                                    expected_checksum=int(expected_crc),
                                    actual_checksum=actual_crc32)
