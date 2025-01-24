#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# This file is distributed under the terms of the Apache License 2.0
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import sys

# Installing `pyproj` Conda packages requires to set `PROJ_LIB`

is_win = sys.platform.startswith('win')
if is_win:

    proj_data = os.path.join(sys._MEIPASS, 'Library', 'share', 'proj')

else:
    proj_data = os.path.join(sys._MEIPASS, 'share', 'proj')

if os.path.exists(proj_data):
    os.environ['PROJ_LIB'] = proj_data
