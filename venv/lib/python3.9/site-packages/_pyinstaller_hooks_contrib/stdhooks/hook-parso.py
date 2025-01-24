# -----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# -----------------------------------------------------------------------------

# Hook for Parso, a static analysis tool https://pypi.org/project/jedi/ (IPython dependency)

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('parso')
