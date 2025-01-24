# ------------------------------------------------------------------
# Copyright (c) 2024 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

import os

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# Collect default icon from `resources`, and license/readme file from  `toga_winforms/libs/WebView2`. Use the same call
# to also collect bundled WebView2 DLLs from `toga_winforms/libs/WebView2`.
include_patterns = [
    'resources/*',
    'libs/WebView2/*.md',
    'libs/WebView2/*.dll',
]

# The package seems to bundle WebView2 runtimes for x86, x64, and arm64. We need to collect only the one for the
# running platform, which can be reliably identified by `PROCESSOR_ARCHITECTURE` environment variable, which properly
# reflects the processor architecture of running process (even if running x86 python on x64 machine, or x64 python on
# arm64 machine).
machine = os.environ["PROCESSOR_ARCHITECTURE"].lower()
if machine == 'x86':
    include_patterns += ['libs/WebView2/runtimes/win-x86/*']
elif machine == 'amd64':
    include_patterns += ['libs/WebView2/runtimes/win-x64/*']
elif machine == 'arm64':
    include_patterns += ['libs/WebView2/runtimes/win-arm64/*']

datas = collect_data_files('toga_winforms', includes=include_patterns)

# Collect metadata so that the backend can be discovered via `toga.backends` entry-point.
datas += copy_metadata("toga-winforms")
