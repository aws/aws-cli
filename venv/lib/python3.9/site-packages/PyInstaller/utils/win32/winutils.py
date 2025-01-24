#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Utilities for Windows platform.
"""

import os
import sys

import PyInstaller.log as logging
from PyInstaller import compat

logger = logging.getLogger(__name__)


def get_windows_dir():
    """
    Return the Windows directory, e.g., C:\\Windows.
    """
    # Imported here to avoid circular import.
    from PyInstaller import compat
    windir = compat.win32api.GetWindowsDirectory()
    if not windir:
        raise SystemExit("Error: Cannot determine Windows directory!")
    return windir


def get_system_path():
    """
    Return the required Windows system paths.
    """
    # Imported here to avoid circular import.
    from PyInstaller import compat
    _bpath = []
    sys_dir = compat.win32api.GetSystemDirectory()
    # Ensure C:\Windows\system32  and C:\Windows directories are always present in PATH variable.
    # C:\Windows\system32 is valid even for 64-bit Windows. Access do DLLs are transparently redirected to
    # C:\Windows\syswow64 for 64bit applactions.
    # See http://msdn.microsoft.com/en-us/library/aa384187(v=vs.85).aspx
    _bpath = [sys_dir, get_windows_dir()]
    return _bpath


def extend_system_path(paths):
    """
    Add new paths at the beginning of environment variable PATH.

    Some hooks might extend PATH where PyInstaller should look for dlls.
    """
    # imported here to avoid circular import
    from PyInstaller import compat
    old_path = compat.getenv('PATH', '')
    paths.append(old_path)
    new_path = os.pathsep.join(paths)
    compat.setenv('PATH', new_path)


def import_pywin32_module(module_name):
    """
    Import and return the PyWin32 module with the passed name.

    When imported, the `pywintypes` and `pythoncom` modules both internally import dynamic libraries
    (e.g., `pywintypes.py` imports `pywintypes34.dll` under Python 3.4). The Anaconda Python distribution for Windows
    installs these libraries to non-standard directories, resulting in
    `"ImportError: No system module 'pywintypes' (pywintypes34.dll)"`
    exceptions. This function catches these exceptions, searches for these libraries, adds their directories to
    `sys.path`, and retries.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of this module.

    Returns
    ----------
    types.ModuleType
        The desired module.
    """
    module = None

    try:
        module = __import__(module_name, globals={}, locals={}, fromlist=[''])
    except ImportError as exc:
        if str(exc).startswith('No system module'):
            # True if "sys.frozen" is currently set.
            is_sys_frozen = hasattr(sys, 'frozen')

            # Current value of "sys.frozen" if any.
            sys_frozen = getattr(sys, 'frozen', None)

            # Force PyWin32 to search "sys.path" for DLLs. By default, PyWin32 only searches "site-packages\win32\lib",
            # "sys.prefix", and Windows system directories (e.g., "C:\Windows\System32"). This is an ugly hack, but
            # there is no other way.
            sys.frozen = '|_|GLYH@CK'

            # If isolated to a venv, the preferred site.getsitepackages() function is unreliable. Fall back to searching
            # "sys.path" instead.
            if compat.is_venv:
                sys_paths = sys.path
            else:
                sys_paths = compat.getsitepackages()

            for sys_path in sys_paths:
                # Absolute path of the directory containing PyWin32 DLLs.
                pywin32_dll_dir = os.path.join(sys_path, 'pywin32_system32')
                if os.path.isdir(pywin32_dll_dir):
                    sys.path.append(pywin32_dll_dir)
                    try:
                        module = __import__(name=module_name, globals={}, locals={}, fromlist=[''])
                        break
                    except ImportError:
                        pass

            # If "sys.frozen" was previously set, restore its prior value.
            if is_sys_frozen:
                sys.frozen = sys_frozen
            # Else, undo this hack entirely.
            else:
                del sys.frozen

        # If this module remains unimportable, PyWin32 is not installed. Fail.
        if module is None:
            raise

    return module


def convert_dll_name_to_str(dll_name):
    """
    Convert dll names from 'bytes' to 'str'.

    Latest pefile returns type 'bytes'.
    :param dll_name:
    :return:
    """
    # Imported here to avoid circular import.
    if isinstance(dll_name, bytes):
        return str(dll_name, encoding='UTF-8')
    else:
        return dll_name


def set_exe_build_timestamp(exe_path, timestamp):
    """
    Modifies the executable's build timestamp by updating values in the corresponding PE headers.
    """
    import pefile

    with pefile.PE(exe_path, fast_load=True) as pe:
        # Manually perform a full load. We need it to load all headers, but specifying it in the constructor triggers
        # byte statistics gathering that takes forever with large files. So we try to go around that...
        pe.full_load()

        # Set build timestamp.
        # See: https://0xc0decafe.com/malware-analyst-guide-to-pe-timestamps
        timestamp = int(timestamp)
        # Set timestamp field in FILE_HEADER
        pe.FILE_HEADER.TimeDateStamp = timestamp
        # MSVC-compiled executables contain (at least?) one DIRECTORY_ENTRY_DEBUG entry that also contains timestamp
        # with same value as set in FILE_HEADER. So modify that as well, as long as it is set.
        debug_entries = getattr(pe, 'DIRECTORY_ENTRY_DEBUG', [])
        for debug_entry in debug_entries:
            if debug_entry.struct.TimeDateStamp:
                debug_entry.struct.TimeDateStamp = timestamp

        # Generate updated EXE data
        data = pe.write()

    # Rewrite the exe
    with open(exe_path, 'wb') as fp:
        fp.write(data)


def update_exe_pe_checksum(exe_path):
    """
    Compute the executable's PE checksum, and write it to PE headers.

    This optional checksum is supposed to protect the executable against corruption but some anti-viral software have
    taken to flagging anything without it set correctly as malware. See issue #5579.
    """
    import pefile

    # Compute checksum using our equivalent of the MapFileAndCheckSumW - for large files, it is significantly faster
    # than pure-pyton pefile.PE.generate_checksum(). However, it requires the file to be on disk (i.e., cannot operate
    # on a memory buffer).
    try:
        checksum = compute_exe_pe_checksum(exe_path)
    except Exception as e:
        raise RuntimeError("Failed to compute PE checksum!") from e

    # Update the checksum
    with pefile.PE(exe_path, fast_load=True) as pe:
        pe.OPTIONAL_HEADER.CheckSum = checksum

        # Generate updated EXE data
        data = pe.write()

    # Rewrite the exe
    with open(exe_path, 'wb') as fp:
        fp.write(data)


def compute_exe_pe_checksum(exe_path):
    """
    This is a replacement for the MapFileAndCheckSumW function. As noted in MSDN documentation, the Microsoft's
    implementation of MapFileAndCheckSumW internally calls its ASCII variant (MapFileAndCheckSumA), and therefore
    cannot handle paths that contain characters that are not representable in the current code page.
    See: https://docs.microsoft.com/en-us/windows/win32/api/imagehlp/nf-imagehlp-mapfileandchecksumw

    This function is based on Wine's implementation of MapFileAndCheckSumW, and due to being based entirely on
    the pure widechar-API functions, it is not limited by the current code page.
    """
    # ctypes bindings for relevant win32 API functions
    import ctypes
    from ctypes import windll, wintypes

    INVALID_HANDLE = wintypes.HANDLE(-1).value

    GetLastError = ctypes.windll.kernel32.GetLastError
    GetLastError.argtypes = ()
    GetLastError.restype = wintypes.DWORD

    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = (
        wintypes.HANDLE,  # hObject
    )
    CloseHandle.restype = wintypes.BOOL

    CreateFileW = windll.kernel32.CreateFileW
    CreateFileW.argtypes = (
        wintypes.LPCWSTR,  # lpFileName
        wintypes.DWORD,  # dwDesiredAccess
        wintypes.DWORD,  # dwShareMode
        wintypes.LPVOID,  # lpSecurityAttributes
        wintypes.DWORD,  # dwCreationDisposition
        wintypes.DWORD,  # dwFlagsAndAttributes
        wintypes.HANDLE,  # hTemplateFile
    )
    CreateFileW.restype = wintypes.HANDLE

    CreateFileMappingW = windll.kernel32.CreateFileMappingW
    CreateFileMappingW.argtypes = (
        wintypes.HANDLE,  # hFile
        wintypes.LPVOID,  # lpSecurityAttributes
        wintypes.DWORD,  # flProtect
        wintypes.DWORD,  # dwMaximumSizeHigh
        wintypes.DWORD,  # dwMaximumSizeLow
        wintypes.LPCWSTR,  # lpName
    )
    CreateFileMappingW.restype = wintypes.HANDLE

    MapViewOfFile = windll.kernel32.MapViewOfFile
    MapViewOfFile.argtypes = (
        wintypes.HANDLE,  # hFileMappingObject
        wintypes.DWORD,  # dwDesiredAccess
        wintypes.DWORD,  # dwFileOffsetHigh
        wintypes.DWORD,  # dwFileOffsetLow
        wintypes.DWORD,  # dwNumberOfBytesToMap
    )
    MapViewOfFile.restype = wintypes.LPVOID

    UnmapViewOfFile = windll.kernel32.UnmapViewOfFile
    UnmapViewOfFile.argtypes = (
        wintypes.LPCVOID,  # lpBaseAddress
    )
    UnmapViewOfFile.restype = wintypes.BOOL

    GetFileSizeEx = windll.kernel32.GetFileSizeEx
    GetFileSizeEx.argtypes = (
        wintypes.HANDLE,  # hFile
        wintypes.PLARGE_INTEGER,  # lpFileSize
    )

    CheckSumMappedFile = windll.imagehlp.CheckSumMappedFile
    CheckSumMappedFile.argtypes = (
        wintypes.LPVOID,  # BaseAddress
        wintypes.DWORD,  # FileLength
        wintypes.PDWORD,  # HeaderSum
        wintypes.PDWORD,  # CheckSum
    )
    CheckSumMappedFile.restype = wintypes.LPVOID

    # Open file
    hFile = CreateFileW(
        ctypes.c_wchar_p(exe_path),
        0x80000000,  # dwDesiredAccess = GENERIC_READ
        0x00000001 | 0x00000002,  # dwShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,  # lpSecurityAttributes = NULL
        3,  # dwCreationDisposition = OPEN_EXISTING
        0x80,  # dwFlagsAndAttributes = FILE_ATTRIBUTE_NORMAL
        None  # hTemplateFile = NULL
    )
    if hFile == INVALID_HANDLE:
        err = GetLastError()
        raise RuntimeError(f"Failed to open file {exe_path}! Error code: {err}")

    # Query file size
    fileLength = wintypes.LARGE_INTEGER(0)
    if GetFileSizeEx(hFile, fileLength) == 0:
        err = GetLastError()
        CloseHandle(hFile)
        raise RuntimeError(f"Failed to query file size file! Error code: {err}")
    fileLength = fileLength.value
    if fileLength > (2**32 - 1):
        raise RuntimeError("Executable size exceeds maximum allowed executable size on Windows (4 GiB)!")

    # Map the file
    hMapping = CreateFileMappingW(
        hFile,
        None,  # lpFileMappingAttributes = NULL
        0x02,  # flProtect = PAGE_READONLY
        0,  # dwMaximumSizeHigh = 0
        0,  # dwMaximumSizeLow = 0
        None  # lpName = NULL
    )
    if not hMapping:
        err = GetLastError()
        CloseHandle(hFile)
        raise RuntimeError(f"Failed to map file! Error code: {err}")

    # Create map view
    baseAddress = MapViewOfFile(
        hMapping,
        4,  # dwDesiredAccess = FILE_MAP_READ
        0,  # dwFileOffsetHigh = 0
        0,  # dwFileOffsetLow = 0
        0  # dwNumberOfBytesToMap = 0
    )
    if baseAddress == 0:
        err = GetLastError()
        CloseHandle(hMapping)
        CloseHandle(hFile)
        raise RuntimeError(f"Failed to create map view! Error code: {err}")

    # Finally, compute the checksum
    headerSum = wintypes.DWORD(0)
    checkSum = wintypes.DWORD(0)
    ret = CheckSumMappedFile(baseAddress, fileLength, ctypes.byref(headerSum), ctypes.byref(checkSum))
    if ret is None:
        err = GetLastError()

    # Cleanup
    UnmapViewOfFile(baseAddress)
    CloseHandle(hMapping)
    CloseHandle(hFile)

    if ret is None:
        raise RuntimeError(f"CheckSumMappedFile failed! Error code: {err}")

    return checkSum.value
