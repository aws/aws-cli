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
#
# cel-python is Pure Python implementation of Google Common Expression Language,
# https://opensource.google/projects/cel
# This implementation has minimal dependencies, runs quickly, and can be embedded into Python-based applications.
# Specifically, the intent is to be part of Cloud Custodian, C7N, as part of the security policy filter.
# https://github.com/cloud-custodian/cel-python
#
# Tested with cel-python 0.1.5

from PyInstaller.utils.hooks import collect_data_files

# Collect *.lark file(s) from the package
datas = collect_data_files('celpy')
