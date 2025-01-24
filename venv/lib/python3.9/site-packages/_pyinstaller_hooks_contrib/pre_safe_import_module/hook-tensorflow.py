#-----------------------------------------------------------------------------
# Copyright (c) 2022, PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import is_module_satisfies


def pre_safe_import_module(api):
    # As of tensorflow 2.8.0, the `tensorflow.keras` is entirely gone, replaced by a lazy-loaded alias for
    # `keras.api._v2.keras`. Without us registering the alias here, a program that imports only from
    # `tensorflow.keras` fails to collect `tensorflow`.
    # See: https://github.com/pyinstaller/pyinstaller/discussions/6890
    # The alias was already present in earlier releases, but it does not seem to be causing problems there,
    # so keep this specific to tensorflow >= 2.8.0 to avoid accidentally breaking something else.
    #
    # Starting with tensorflow 2.16.0, the alias points to `keras._tf_keras.keras`.
    if is_module_satisfies("tensorflow >= 2.16.0"):
        api.add_alias_module('keras._tf_keras.keras', 'tensorflow.keras')
    elif is_module_satisfies("tensorflow >= 2.8.0"):
        api.add_alias_module('keras.api._v2.keras', 'tensorflow.keras')
