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

    # Special handling is needed only on macOS.
    if sys.platform != 'darwin':
        return

    # See ``pyi_rth_qt5.py`: use a "standard" PyQt5 layout.
    # Try PyQt5 5.15.4-style path first...
    pyqt_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5')
    if not os.path.isdir(pyqt_path):
        # ... and fall back to the older version
        pyqt_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt')

    # If QtWebEngineProcess was collected from a framework-based Qt build, we need to set QTWEBENGINEPROCESS_PATH.
    # If not (a dylib-based build; Anaconda on macOS), it should be found automatically, same as on other OSes.
    process_path = os.path.normpath(
        os.path.join(
            pyqt_path, 'lib', 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS',
            'QtWebEngineProcess'
        )
    )
    if os.path.exists(process_path):
        os.environ['QTWEBENGINEPROCESS_PATH'] = process_path


_pyi_rthook()
del _pyi_rthook
