#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# This file is distributed under the terms of the Apache License 2.0
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import sys
import os
import nltk

#add the path to nltk_data
nltk.data.path.insert(0, os.path.join(sys._MEIPASS, "nltk_data"))
