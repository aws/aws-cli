from tests import unittest

from botocore.retries import bucket
from botocore.exceptions import CapacityNotAvailableError


class FakeClock(bucket.Clock):
    def __init__(self, timestamp_sequences):
        self.timestamp_sequences = timestamp_sequences
        self.sleep_call_amounts = []

    def sleep(self, amount):
        self.sleep_call_amounts.append(amount)

    def current_time(self):
        return self.timestamp_sequences.pop(0)


class TestTokenBucket(unittest.TestCase):
    def setUp(self):
        self.timestamp_sequences = [0]
        self.clock = FakeClock(self.timestamp_sequences)

    def create_token_bucket(self, max_rate=10, min_rate=0.1):
        return bucket.TokenBucket(max_rate=max_rate, clock=self.clock,
                                  min_rate=min_rate)

    def test_can_acquire_amount(self):
        self.timestamp_sequences.extend([
            # Requests tokens every second, which is well below our
            # 10 TPS fill rate.
            1,
            2,
            3,
            4,
            5,
        ])
        token_bucket = self.create_token_bucket(max_rate=10)
        for _ in range(5):
            self.assertTrue(token_bucket.acquire(1, block=False))

    def test_can_change_max_capacity_lower(self):
        # Requests at 1 TPS.
        self.timestamp_sequences.extend([1, 2, 3, 4, 5])
        token_bucket = self.create_token_bucket(max_rate=10)
        # Request the first 5 tokens with max_rate=10
        for _ in range(5):
            self.assertTrue(token_bucket.acquire(1, block=False))
        # Now scale the max_rate down to 1 on the 5th second.
        self.timestamp_sequences.append(5)
        token_bucket.max_rate = 1
        # And then from seconds 6-10 we request at one per second.
        self.timestamp_sequences.extend([6, 7, 8, 9, 10])
        for _ in range(5):
            self.assertTrue(token_bucket.acquire(1, block=False))

    def test_max_capacity_is_at_least_one(self):
        token_bucket = self.create_token_bucket()
        self.timestamp_sequences.append(1)
        token_bucket.max_rate = 0.5
        self.assertEqual(token_bucket.max_rate, 0.5)
        self.assertEqual(token_bucket.max_capacity, 1)

    def test_acquire_fails_on_non_block_mode_returns_false(self):
        self.timestamp_sequences.extend([
            # Initial creation time.
            0,
            # Requests a token 1 second later.
            1
        ])
        token_bucket = self.create_token_bucket(max_rate=10)
        with self.assertRaises(CapacityNotAvailableError):
            token_bucket.acquire(100, block=False)

    def test_can_retrieve_at_max_send_rate(self):
        self.timestamp_sequences.extend([
            # Request a new token every 100ms (10 TPS) for 2 seconds.
            1 + 0.1 * i for i in range(20)
        ])
        token_bucket = self.create_token_bucket(max_rate=10)
        for _ in range(20):
            self.assertTrue(token_bucket.acquire(1, block=False))

    def test_acquiring_blocks_when_capacity_reached(self):
        # This is 1 token every 0.1 seconds.
        token_bucket = self.create_token_bucket(max_rate=10)
        self.timestamp_sequences.extend([
            # The first acquire() happens after .1 seconds.
            0.1,
            # The second acquire() will fail because we get tokens at
            # 1 per 0.1 seconds.  We will then sleep for 0.05 seconds until we
            # get a new token.
            0.15,
            # And at 0.2 seconds we get our token.
            0.2,
            # And at 0.3 seconds we have no issues getting a token.
            # Because we're using such small units (to avoid bloating the
            # test run time), we have to go slightly over 0.3 seconds here.
            0.300001,
        ])
        self.assertTrue(token_bucket.acquire(1, block=False))
        self.assertEqual(token_bucket.available_capacity, 0)
        self.assertTrue(token_bucket.acquire(1, block=True))
        self.assertEqual(token_bucket.available_capacity, 0)
        self.assertTrue(token_bucket.acquire(1, block=False))

    def test_rate_cant_go_below_min(self):
        token_bucket = self.create_token_bucket(max_rate=1, min_rate=0.2)
        self.timestamp_sequences.append(1)
        token_bucket.max_rate = 0.1
        self.assertEqual(token_bucket.max_rate, 0.2)
        self.assertEqual(token_bucket.max_capacity, 1)
