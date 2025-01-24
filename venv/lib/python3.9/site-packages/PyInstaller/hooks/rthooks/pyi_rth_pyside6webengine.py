#-----------------------------------------------------------------------------
# Copyright (c) 2015-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------


def _pyi_rthook():
    import os
    import sys

    if sys.platform != 'darwin':
        return

    # If QtWebEngineProcess was collected from a framework-based Qt build, we need to set QTWEBENGINEPROCESS_PATH.
    # If not (a dylib-based build; Anaconda on macOS), it should be found automatically, same as on other OSes.
    process_path = os.path.normpath(
        os.path.join(
            sys._MEIPASS, 'PySide6', 'Qt', 'lib', 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app',
            'Contents', 'MacOS', 'QtWebEngineProcess'
        )
    )
    if os.path.exists(process_path):
        os.environ['QTWEBENGINEPROCESS_PATH'] = process_path

        # As of Qt 6.3.1, we need to disable sandboxing to make QtWebEngineProcess to work at all with the way
        # PyInstaller currently collects libraries from Qt .framework bundles.
        # This runtime hook should avoid importing PySide6, so we have no way of querying the version, and always
        # disable sandboxing.
        os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'


_pyi_rthook()
del _pyi_rthook
