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

from PyInstaller.compat import is_py311
from PyInstaller.utils.hooks import is_module_satisfies

hiddenimports = [
    'cgi',
    'falcon.app_helpers',
    'falcon.forwarded',
    'falcon.media',
    'falcon.request_helpers',
    'falcon.responders',
    'falcon.response_helpers',
    'falcon.routing',
    'falcon.vendor.mimeparse',
    'falcon.vendor',
    'uuid',
    'xml.etree.ElementTree',
    'xml.etree'
]

# falcon v4.0.0 added couple of more cythonized modules that depend on the following stdlib modules.
if is_module_satisfies('falcon >= 4.0.0'):
    hiddenimports += [
        'dataclasses',
        'json',
    ]

    # `wsgiref.types` is available (and thus referenced) only under python >= 3.11.
    if is_py311:
        hiddenimports += ['wsgiref.types']
