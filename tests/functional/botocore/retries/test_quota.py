import random
import threading
import time

from botocore.retries import quota
from tests import unittest


class TestRetryQuota(unittest.TestCase):
    def setUp(self):
        self.max_capacity = 50
        self.retry_quota = quota.RetryQuota(self.max_capacity)
        self.shutdown_threads = False
        self.seen_capacities = []

    def run_in_thread(self):
        while not self.shutdown_threads:
            capacity = random.randint(1, self.max_capacity)
            self.retry_quota.acquire(capacity)
            self.seen_capacities.append(self.retry_quota.available_capacity)
            self.retry_quota.release(capacity)
            self.seen_capacities.append(self.retry_quota.available_capacity)

    def test_capacity_stays_within_range(self):
        # The main thing we're after is that the available_capacity
        # should always be 0 <= capacity <= max_capacity.
        # So what we do is spawn a number of threads and them acquire
        # random capacity.  They'll check that they never see an invalid
        # capacity.
        threads = []
        for i in range(10):
            threads.append(threading.Thread(target=self.run_in_thread))
        for thread in threads:
            thread.start()
        # We'll let things run for a second.
        time.sleep(1)
        self.shutdown_threads = True
        for thread in threads:
            thread.join()
        for seen_capacity in self.seen_capacities:
            self.assertGreaterEqual(seen_capacity, 0)
            self.assertLessEqual(seen_capacity, self.max_capacity)
