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

# Hook for https://github.com/IdentityPython/pysaml2
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

datas = copy_metadata("pysaml2")

# The library contains a bunch of XSD schemas that are loaded by the code:
# https://github.com/IdentityPython/pysaml2/blob/7cb4f09dce87a7e8098b9c7552ebab8bc77bc896/src/saml2/xml/schema/__init__.py#L23
# On the other hand, runtime tools are not needed.
datas += collect_data_files("saml2", excludes=["**/tools"])

# Submodules are loaded dynamically by:
# https://github.com/IdentityPython/pysaml2/blob/7cb4f09dce87a7e8098b9c7552ebab8bc77bc896/src/saml2/attribute_converter.py#L52
hiddenimports = collect_submodules("saml2.attributemaps")
