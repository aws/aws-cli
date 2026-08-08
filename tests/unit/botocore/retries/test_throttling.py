from botocore.retries import throttling
from tests import unittest


class TestCubicCalculator(unittest.TestCase):
    def create_cubic_calculator(
        self, starting_max_rate=10, beta=0.7, scale_constant=0.4
    ):
        return throttling.CubicCalculator(
            starting_max_rate=starting_max_rate,
            scale_constant=scale_constant,
            start_time=0,
            beta=beta,
        )

    # For these tests, rather than duplicate the formulas in the tests,
    # I want to check against a fixed set of inputs with by-hand verified
    # values to ensure we're doing the calculations correctly.

    def test_starting_params(self):
        cubic = self.create_cubic_calculator(starting_max_rate=10)
        self.assertAlmostEqual(
            cubic.get_params_snapshot().k, 1.9574338205844317
        )

    def test_success_responses_until_max_hit(self):
        # For this test we're interested in the behavior less so than
        # the specific numbers.  There's a few cases we care about:
        #
        cubic = self.create_cubic_calculator(starting_max_rate=10)
        params = cubic.get_params_snapshot()
        start_k = params.k
        start_w_max = params.w_max
        # Before we get to t == start_k, our throttle is below our
        # max w_max
        assertLessEqual = self.assertLessEqual
        assertLessEqual(cubic.success_received(start_k / 3.0), start_w_max)
        assertLessEqual(cubic.success_received(start_k / 2.0), start_w_max)
        assertLessEqual(cubic.success_received(start_k / 1.1), start_w_max)
        # At t == start_k, we should be at w_max.
        self.assertAlmostEqual(cubic.success_received(timestamp=start_k), 10.0)
        # And once we pass start_k, we'll be above w_max.
        self.assertGreaterEqual(
            cubic.success_received(start_k * 1.1), start_w_max
        )
        self.assertGreaterEqual(
            cubic.success_received(start_k * 2.0), start_w_max
        )

    def test_error_response_decreases_rate_by_beta(self):
        # This is the default value here so we're just being explicit.
        cubic = self.create_cubic_calculator(starting_max_rate=10, beta=0.7)

        # So let's say we made it up to 8 TPS before we were throttled.
        rate_when_throttled = 8
        new_rate = cubic.error_received(
            current_rate=rate_when_throttled, timestamp=1
        )
        self.assertAlmostEqual(new_rate, rate_when_throttled * 0.7)

        new_params = cubic.get_params_snapshot()
        self.assertEqual(
            new_params,
            throttling.CubicParams(
                w_max=rate_when_throttled, k=1.8171205928321397, last_fail=1
            ),
        )

    def test_t_0_should_match_beta_decrease(self):
        # So if I have beta of 0.6
        cubic = self.create_cubic_calculator(starting_max_rate=10, beta=0.6)
        # When I get throttled I should decrease my rate by 60%.
        new_rate = cubic.error_received(current_rate=10, timestamp=1)
        self.assertEqual(new_rate, 6.0)
        # And my starting rate at time t=1 should start at that new rate.
        self.assertAlmostEqual(cubic.success_received(timestamp=1), 6.0)
