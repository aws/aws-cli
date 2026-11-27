# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Skip decorators for credential daemon tests, in the style of
``awscli.testutils.skip_if_windows``."""

import os
import platform
import unittest


def skip_unless_linux(reason):
    """Skip a test that runs only on Linux, such as one that uses a Linux
    socket path."""
    return unittest.skipIf(platform.system() != 'Linux', reason)


def skip_if_root(reason):
    """Skip a test that relies on file or socket permissions, which root
    ignores."""
    return unittest.skipIf(
        hasattr(os, 'geteuid') and os.geteuid() == 0, reason
    )
