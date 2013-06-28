import time
import random
import functools


def delay_exponential(base, growth_factor, attempts):
    if base == 'rand':
        base = random.random()
    time_to_sleep = base * (growth_factor ** (attempts - 1))
    return time_to_sleep


def create_exponential_delay_function(base, growth_factor):
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
    if '__default__' in config:
        policies = config['__default__'].get('policies', [])
        max_attempts = config['__default__']['max_attempts']
        for key in policies:
            checkers.append(_create_single_checker(policies[key]))
    if operation_name is not None and config.get(operation_name) is not None:
        operation_policies = config[operation_name]['policies']
        for key in operation_policies:
            checkers.append(_create_single_checker(operation_policies[key]))
    if len(checkers) == 1:
        # Don't need to use a MultiChecker
        return MaxAttemptsDecorator(checkers[0], max_attempts=max_attempts)
    else:
        multi_checker = MultiChecker(checkers)
        return MaxAttemptsDecorator(multi_checker, max_attempts=max_attempts)


def _create_single_checker(config):
    response = config['applies_when']['response']
    if 'service_error_code' in response:
        checker = ServiceErrorCodeChecker(
            status_code=response['http_status_code'],
            error_code=response['service_error_code'])
    elif 'http_status_code' in response:
        raise NotImplementedError()
    elif 'crc32body' in response:
        checker = CRC32Checker(header=response['crc32body'])
    else:
        raise ValueError("Unknown retry policy: %s" % config)
    return checker


class RetryHandler(object):
    """
    Super simple retry handler.
    Pass in the callable to be retried and another callable, the statusfn.
    The statusfn will get called with the attempt number and the return
    value and is responsible for performing any kind of delay needed.  It
    should also return a boolean, True if the retryable needs to be
    retried and False if it does not.
    """

    def __init__(self, checker, action):
        self._checker = checker
        self._action = action

    def __call__(self, response, attempts, **kwargs):
        if self._checker(response, attempts):
            return self._action(attempts=attempts)


class MaxAttemptsDecorator(object):
    def __init__(self, checker, max_attempts):
        self._checker = checker
        self._max_attempts = max_attempts

    def __call__(self, response, attempt_number):
        print("MaxAttemptsDecorator")
        should_retry = self._checker(response, attempt_number)
        if should_retry:
            if attempt_number >= self._max_attempts:
                return False
            else:
                return should_retry
        else:
            return False


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
        self._header = header

    def __call__(self, response, attempt_number):
        pass
