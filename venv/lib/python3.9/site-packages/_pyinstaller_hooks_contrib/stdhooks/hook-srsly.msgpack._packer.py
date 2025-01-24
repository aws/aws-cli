# ------------------------------------------------------------------
# Copyright (c) 2021 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------
"""
srsly.msgpack._packer contains hidden imports which are needed to import it
This hook was created to make spacy work correctly.
"""

hiddenimports = ['srsly.msgpack.util']
