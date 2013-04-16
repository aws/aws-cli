import time
import random


def delay_exponential(attempts):
    time.sleep(random.random() * (2 ** attempts))


class RetryHandler(object):
    """
    Super simple retry handler.
    Pass in the callable to be retried and another callable, the statusfn.
    The statusfn will get called with the attempt number and the return
    value and is responsible for performing any kind of delay needed.  It
    should also return a boolean, True if the retryable needs to be
    retried and False if it does not.
    """

    def __init__(self, retryable, statusfn):
        self.retryable = retryable
        self.statusfn = statusfn
        self.attempts = 0

    def __call__(self, *args, **kwargs):
        retry = True
        while retry:
            return_value = self.retryable(*args, **kwargs)
            self.attempts += 1
            retry = self.statusfn(self.attempts, return_value)
        return return_value
