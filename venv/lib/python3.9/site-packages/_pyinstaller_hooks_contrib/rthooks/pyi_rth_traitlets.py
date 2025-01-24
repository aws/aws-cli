#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# This file is distributed under the terms of the Apache License 2.0
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# 'traitlets' uses module 'inspect' from default Python library to inspect
# source code of modules. However, frozen app does not contain source code
# of Python modules.
#
# hook-IPython depends on module 'traitlets'.

import traitlets.traitlets


def _disabled_deprecation_warnings(method, cls, method_name, msg):
    pass


traitlets.traitlets._deprecated_method = _disabled_deprecation_warnings
