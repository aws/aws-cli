#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# The path to Qt's components may not default to the wheel layout for self-compiled PyQt6 installations. Mandate the
# wheel layout. See ``utils/hooks/qt.py`` for more details.


def _pyi_rthook():
    import os
    import sys

    # Try PyQt6 6.0.3-style path first...
    pyqt_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt6')
    if not os.path.isdir(pyqt_path):
        # ... and fall back to the older version.
        pyqt_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt')
    os.environ['QT_PLUGIN_PATH'] = os.path.join(pyqt_path, 'plugins')
    os.environ['QML2_IMPORT_PATH'] = os.path.join(pyqt_path, 'qml')
    # Modelled after similar PATH modification in PyQt5 rthook. With PyQt6, this modification seems necessary for SSL
    # DLLs to be found in onefile builds.
    if sys.platform.startswith('win') and 'PATH' in os.environ:
        os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']


_pyi_rthook()
del _pyi_rthook
