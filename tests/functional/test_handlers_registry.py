# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Verify that awscli/handlers_registry.py is up to date.

If this test fails, re-run the generation script and commit the result:

    scripts/generate_plugin_registry
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SCRIPT = os.path.join(REPO_ROOT, 'scripts', 'generate_plugin_registry')


def test_handlers_registry_matches_generation_script():
    result = subprocess.run(
        [sys.executable, SCRIPT, '--check'],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        'awscli/handlers_registry.py is out of date.\n'
        'Re-generate it by running:\n\n'
        '    scripts/generate_plugin_registry\n\n'
        f'Script output:\n{result.stdout}{result.stderr}'
    )
