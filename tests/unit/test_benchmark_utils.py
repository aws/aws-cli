# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import sys
import tempfile
import unittest
from unittest import mock

# Add the scripts directory to the path so we can import benchmark_utils
scripts_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'scripts',
    'performance'
)
sys.path.insert(0, scripts_dir)

import benchmark_utils  # noqa: E402


class TestSummarize(unittest.TestCase):
    """Test cases for the summarize function."""

    @mock.patch('benchmark_utils.subprocess.check_call')
    def test_summarize_does_not_mutate_args(self, mock_check_call):
        """Verify that summarize() does not mutate the argument list.

        The function should use a new list for the JSON output call
        rather than extending the original argument list.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result_dir = os.path.join(tmpdir, 'results')
            summary_dir = os.path.join(tmpdir, 'summary')
            os.makedirs(result_dir)
            os.makedirs(summary_dir)

            # Create a dummy CSV file in result_dir
            test_file = os.path.join(result_dir, 'test.csv')
            with open(test_file, 'w') as f:
                f.write('dummy,data\n')

            script = '/path/to/summarize'

            # Capture the arguments passed to each check_call invocation
            call_args_list = []

            def capture_args(args, **kwargs):
                # Make a copy to capture the state at call time
                call_args_list.append(list(args))

            mock_check_call.side_effect = capture_args

            benchmark_utils.summarize(script, result_dir, summary_dir)

            # Verify we had exactly 2 calls
            self.assertEqual(len(call_args_list), 2)

            # First call should have: [script, test_file]
            first_call_args = call_args_list[0]
            self.assertEqual(first_call_args[0], script)
            self.assertIn(test_file, first_call_args)
            self.assertNotIn('--output-format', first_call_args)

            # Second call should have: [script, test_file, --output-format, json]  # noqa: E501
            second_call_args = call_args_list[1]
            self.assertEqual(second_call_args[0], script)
            self.assertIn(test_file, second_call_args)
            self.assertIn('--output-format', second_call_args)
            self.assertIn('json', second_call_args)

    @mock.patch('benchmark_utils.subprocess.check_call')
    def test_summarize_multiple_calls_are_independent(self, mock_check_call):
        """Verify that multiple calls to summarize() are independent.

        This tests the scenario from issue #10121 where calling summarize()
        multiple times could result in duplicated CLI arguments if the
        original list was mutated.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result_dir = os.path.join(tmpdir, 'results')
            summary_dir = os.path.join(tmpdir, 'summary')
            os.makedirs(result_dir)
            os.makedirs(summary_dir)

            test_file = os.path.join(result_dir, 'test.csv')
            with open(test_file, 'w') as f:
                f.write('dummy,data\n')

            script = '/path/to/summarize'
            call_args_list = []

            def capture_args(args, **kwargs):
                call_args_list.append(list(args))

            mock_check_call.side_effect = capture_args

            # Call summarize twice
            benchmark_utils.summarize(script, result_dir, summary_dir)
            benchmark_utils.summarize(script, result_dir, summary_dir)

            # Should have 4 calls total (2 per summarize invocation)
            self.assertEqual(len(call_args_list), 4)

            # Check that neither of the JSON calls have duplicated flags
            for i, args in enumerate(call_args_list):
                output_format_count = args.count('--output-format')
                # Each call should have at most 1 --output-format flag
                msg = f"Call {i} has {output_format_count} flags: {args}"
                self.assertLessEqual(output_format_count, 1, msg)


if __name__ == '__main__':
    unittest.main()
