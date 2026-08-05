import random
import threading
import time

from botocore.retries import bucket
from tests import unittest


class InstrumentedTokenBucket(bucket.TokenBucket):
    def _acquire(self, amount, block):
        rval = super()._acquire(amount, block)
        assert self._current_capacity >= 0
        return rval


class TestTokenBucketThreading(unittest.TestCase):
    def setUp(self):
        self.shutdown_threads = False
        self.caught_exceptions = []
        self.acquisitions_by_thread = {}

    def run_in_thread(self):
        while not self.shutdown_threads:
            capacity = random.randint(1, self.max_capacity)
            self.retry_quota.acquire(capacity)
            self.seen_capacities.append(self.retry_quota.available_capacity)
            self.retry_quota.release(capacity)
            self.seen_capacities.append(self.retry_quota.available_capacity)

    def create_clock(self):
        return bucket.Clock()

    def test_can_change_max_rate_while_blocking(self):
        # This isn't a stress test, we just want to verify we can change
        # the rate at which we acquire a token.
        min_rate = 0.1
        max_rate = 1
        token_bucket = bucket.TokenBucket(
            min_rate=min_rate,
            max_rate=max_rate,
            clock=self.create_clock(),
        )
        # First we'll set the max_rate to 0.1 (min_rate).  This means that
        # it will take 10 seconds to accumulate a single token.  We'll start
        # a thread and have it acquire() a token.
        # Then in the main thread we'll change the max_rate to something
        # really quick (e.g 100).  We should immediately get a token back.
        # This is going to be timing sensitive, but we can verify that
        # as long as it doesn't take 10 seconds to get a token, we were
        # able to update the rate as needed.
        thread = threading.Thread(target=token_bucket.acquire)
        token_bucket.max_rate = min_rate
        start_time = time.time()
        thread.start()
        # This shouldn't block the main thread.
        token_bucket.max_rate = 100
        thread.join()
        end_time = time.time()
        self.assertLessEqual(end_time - start_time, 1.0 / min_rate)

    def acquire_in_loop(self, token_bucket):
        while not self.shutdown_threads:
            try:
                self.assertTrue(token_bucket.acquire())
                thread_name = threading.current_thread().name
                self.acquisitions_by_thread[thread_name] += 1
            except Exception as e:
                self.caught_exceptions.append(e)

    def randomly_set_max_rate(self, token_bucket, min_val, max_val):
        while not self.shutdown_threads:
            new_rate = random.randint(min_val, max_val)
            token_bucket.max_rate = new_rate
            time.sleep(0.01)

    def test_stress_test_token_bucket(self):
        token_bucket = InstrumentedTokenBucket(
            max_rate=10,
            clock=self.create_clock(),
        )
        all_threads = []
        for _ in range(2):
            all_threads.append(
                threading.Thread(
                    target=self.randomly_set_max_rate,
                    args=(token_bucket, 30, 200),
                )
            )
        for _ in range(10):
            t = threading.Thread(
                target=self.acquire_in_loop, args=(token_bucket,)
            )
            self.acquisitions_by_thread[t.name] = 0
            all_threads.append(t)
        for thread in all_threads:
            thread.start()
        try:
            # If you're working on this code you can bump this number way
            # up to stress test it more locally.
            time.sleep(3)
        finally:
            self.shutdown_threads = True
            for thread in all_threads:
                thread.join()
        # Verify all threads complete sucessfully
        self.assertEqual(self.caught_exceptions, [])
