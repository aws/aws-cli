# ------------------------------------------------------------------
# Copyright (c) 2020 PyInstaller Development Team.
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
Hook for cryptography module from the Python Cryptography Authority.
"""

import os
import glob
import pathlib

from PyInstaller import compat
from PyInstaller import isolated
from PyInstaller.utils.hooks import (
    collect_submodules,
    copy_metadata,
    get_module_file_attribute,
    is_module_satisfies,
    logger,
)

# get the package data so we can load the backends
datas = copy_metadata('cryptography')

# Add the backends as hidden imports
hiddenimports = collect_submodules('cryptography.hazmat.backends')

# Add the OpenSSL FFI binding modules as hidden imports
hiddenimports += collect_submodules('cryptography.hazmat.bindings.openssl') + ['_cffi_backend']


# Include the cffi extensions as binaries in a subfolder named like the package.
# The cffi verifier expects to find them inside the package directory for
# the main module. We cannot use hiddenimports because that would add the modules
# outside the package.
# NOTE: this is not true anymore with PyInstaller >= 6.0, but we keep it like this for compatibility with 5.x series.
binaries = []
cryptography_dir = os.path.dirname(get_module_file_attribute('cryptography'))
for ext in compat.EXTENSION_SUFFIXES:
    ffimods = glob.glob(os.path.join(cryptography_dir, '*_cffi_*%s*' % ext))
    for f in ffimods:
        binaries.append((f, 'cryptography'))


# Check if cryptography was built with support for OpenSSL >= 3.0.0. In that case, we might need to collect external
# OpenSSL modules, if OpenSSL was built with modules support. It seems the best indication of this is the presence
# of ossl-modules directory next to the OpenSSL shared library.
try:
    @isolated.decorate
    def _check_cryptography_openssl3():
        from cryptography.hazmat.backends.openssl.backend import backend
        openssl_version = backend.openssl_version_number()
        return openssl_version >= 0x30000000

    uses_openssl3 = _check_cryptography_openssl3()
except Exception:
    logger.warning(
        "hook-cryptography: failed to determine whether cryptography is using OpenSSL >= 3.0.0", exc_info=True
    )
    uses_openssl3 = False

if uses_openssl3:
    # Determine location of OpenSSL shared library.
    # This requires the new PyInstaller.bindepend API from PyInstaller >= 6.0.
    openssl_lib = None
    if is_module_satisfies("PyInstaller >= 6.0"):
        from PyInstaller.depend import bindepend

        if compat.is_win:
            # Resolve the given library name; first, search the python library directory for python-provided OpenSSL.
            lib_name = 'libssl-3-x64.dll' if compat.is_64bits else 'libssl-3.dll'
            openssl_lib = bindepend.resolve_library_path(lib_name, search_paths=[compat.base_prefix])
        elif compat.is_darwin:
            # First, attempt to resolve using only {sys.base_prefix}/lib - `bindepend.resolve_library_path` uses
            # standard dyld search semantics and uses the given search paths as fallback (and would therefore
            # favor Homebrew-provided version of the library).
            lib_name = 'libssl.3.dylib'
            base_prefix_lib_dir = os.path.join(compat.base_prefix, 'lib')
            openssl_lib = bindepend._resolve_library_path_in_search_paths(lib_name, search_paths=[base_prefix_lib_dir])
            if openssl_lib is None:
                openssl_lib = bindepend.resolve_library_path(lib_name, search_paths=[base_prefix_lib_dir])
        else:
            # Linux and other POSIX systems
            lib_name = 'libssl.so.3'
            openssl_lib = bindepend.resolve_library_path(lib_name)
            if openssl_lib is None and compat.is_musl:
                # Work-around for bug in `bindepend.resolve_library_path` in PyInstaller 6.x, <= 6.6; for search without
                # ldconfig cache (for example, with musl libc on Alpine linux), we need library name without suffix.
                lib_name = 'libssl'
                openssl_lib = bindepend.resolve_library_path(lib_name)
    else:
        logger.warning(
            "hook-cryptography: full support for cryptography + OpenSSL >= 3.0.0 requires PyInstaller >= 6.0"
        )

    # Check for presence of ossl-modules directory next to the OpenSSL shared library.
    if openssl_lib:
        logger.debug("hook-cryptography: OpenSSL shared library location: %r", openssl_lib)

        openssl_lib_dir = pathlib.Path(openssl_lib).parent

        # Collect whole ossl-modules directory, if it exists.
        ossl_modules_dir = openssl_lib_dir / 'ossl-modules'

        # Msys2/MinGW installations on Windows put the shared library into `bin` directory, but the modules are
        # located in `lib` directory. Account for that possibility.
        if not ossl_modules_dir.is_dir() and openssl_lib_dir.name == 'bin':
            ossl_modules_dir = openssl_lib_dir.parent / 'lib' / 'ossl-modules'

        # On Alpine linux, the true location of shared library is /lib directory, but the modules' directory is located
        # in /usr/lib instead. Account for that possibility.
        if not ossl_modules_dir.is_dir() and openssl_lib_dir == pathlib.Path('/lib'):
            ossl_modules_dir = pathlib.Path('/usr/lib/ossl-modules')

        if ossl_modules_dir.is_dir():
            logger.debug("hook-cryptography: collecting OpenSSL modules directory: %r", str(ossl_modules_dir))
            binaries.append((str(ossl_modules_dir), 'ossl-modules'))
