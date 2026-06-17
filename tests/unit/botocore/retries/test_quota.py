from botocore.retries import quota
from tests import unittest


class TestRetryQuota(unittest.TestCase):
    def setUp(self):
        self.retry_quota = quota.RetryQuota(50)

    def test_can_acquire_amount(self):
        self.assertTrue(self.retry_quota.acquire(5))
        self.assertEqual(self.retry_quota.available_capacity, 45)

    def test_can_release_amount(self):
        self.assertTrue(self.retry_quota.acquire(5))
        self.assertEqual(self.retry_quota.available_capacity, 45)
        self.retry_quota.release(5)
        self.assertEqual(self.retry_quota.available_capacity, 50)

    def test_cant_exceed_max_capacity(self):
        self.assertTrue(self.retry_quota.acquire(5))
        self.assertEqual(self.retry_quota.available_capacity, 45)
        self.retry_quota.release(10)
        self.assertEqual(self.retry_quota.available_capacity, 50)

    def test_noop_if_at_max_capacity(self):
        self.retry_quota.release(10)
        self.assertEqual(self.retry_quota.available_capacity, 50)

    def test_cant_go_below_zero(self):
        self.assertTrue(self.retry_quota.acquire(49))
        self.assertEqual(self.retry_quota.available_capacity, 1)
        self.assertFalse(self.retry_quota.acquire(10))
        self.assertEqual(self.retry_quota.available_capacity, 1)
