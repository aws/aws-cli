#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# **NOTE** This module is used during bootstrap.
# Import *ONLY* builtin modules or modules that are collected into the base_library.zip archive.
# List of built-in modules: sys.builtin_module_names
# List of modules collected into base_library.zip: PyInstaller.compat.PY3_BASE_MODULES

import sys
import os
import struct
import marshal
import zlib

# In Python3, the MAGIC_NUMBER value is available in the importlib module. However, in the bootstrap phase we cannot use
# importlib directly, but rather its frozen variant.
import _frozen_importlib

PYTHON_MAGIC_NUMBER = _frozen_importlib._bootstrap_external.MAGIC_NUMBER

# For decrypting Python modules.
CRYPT_BLOCK_SIZE = 16

# Type codes for PYZ PYZ entries
PYZ_ITEM_MODULE = 0
PYZ_ITEM_PKG = 1
PYZ_ITEM_DATA = 2
PYZ_ITEM_NSPKG = 3  # PEP-420 namespace package


class ArchiveReadError(RuntimeError):
    pass


class Cipher:
    """
    This class is used only to decrypt Python modules.
    """
    def __init__(self):
        # At build-time the key is given to us from inside the spec file. At bootstrap-time, we must look for it
        # ourselves, by trying to import the generated 'pyi_crypto_key' module.
        import pyimod00_crypto_key
        key = pyimod00_crypto_key.key

        assert type(key) is str
        if len(key) > CRYPT_BLOCK_SIZE:
            self.key = key[0:CRYPT_BLOCK_SIZE]
        else:
            self.key = key.zfill(CRYPT_BLOCK_SIZE)
        assert len(self.key) == CRYPT_BLOCK_SIZE

        import tinyaes
        self._aesmod = tinyaes
        # Issue #1663: Remove the AES module from sys.modules list. Otherwise it interferes with using 'tinyaes' module
        # in users' code.
        del sys.modules['tinyaes']

    def __create_cipher(self, iv):
        # The 'AES' class is stateful, and this factory method is used to re-initialize the block cipher class with
        # each call to xcrypt().
        return self._aesmod.AES(self.key.encode(), iv)

    def decrypt(self, data):
        cipher = self.__create_cipher(data[:CRYPT_BLOCK_SIZE])
        return cipher.CTR_xcrypt_buffer(data[CRYPT_BLOCK_SIZE:])


class ZlibArchiveReader:
    """
    Reader for PyInstaller's PYZ (ZlibArchive) archive. The archive is used to store collected byte-compiled Python
    modules, as individually-compressed entries.
    """
    _PYZ_MAGIC_PATTERN = b'PYZ\0'

    def __init__(self, filename, start_offset=None, check_pymagic=False):
        self._filename = filename
        self._start_offset = start_offset

        self.toc = {}

        self.cipher = None

        # Try to create Cipher() instance; if encryption is not enabled, pyimod00_crypto_key is not available, and
        # instantiation fails with ImportError.
        try:
            self.cipher = Cipher()
        except ImportError:
            pass

        # If no offset is given, try inferring it from filename
        if start_offset is None:
            self._filename, self._start_offset = self._parse_offset_from_filename(filename)

        # Parse header and load TOC. Standard header contains 12 bytes: PYZ magic pattern, python bytecode magic
        # pattern, and offset to TOC (32-bit integer). It might be followed by additional fields, depending on
        # implementation version.
        with open(self._filename, "rb") as fp:
            # Read PYZ magic pattern, located at the start of the file
            fp.seek(self._start_offset, os.SEEK_SET)

            magic = fp.read(len(self._PYZ_MAGIC_PATTERN))
            if magic != self._PYZ_MAGIC_PATTERN:
                raise ArchiveReadError("PYZ magic pattern mismatch!")

            # Read python magic/version number
            pymagic = fp.read(len(PYTHON_MAGIC_NUMBER))
            if check_pymagic and pymagic != PYTHON_MAGIC_NUMBER:
                raise ArchiveReadError("Python magic pattern mismatch!")

            # Read TOC offset
            toc_offset, *_ = struct.unpack('!i', fp.read(4))

            # Load TOC
            fp.seek(self._start_offset + toc_offset, os.SEEK_SET)
            self.toc = dict(marshal.load(fp))

    @staticmethod
    def _parse_offset_from_filename(filename):
        """
        Parse the numeric offset from filename, stored as: `/path/to/file?offset`.
        """
        offset = 0

        idx = filename.rfind('?')
        if idx == -1:
            return filename, offset

        try:
            offset = int(filename[idx + 1:])
            filename = filename[:idx]  # Remove the offset from filename
        except ValueError:
            # Ignore spurious "?" in the path (for example, like in Windows UNC \\?\<path>).
            pass

        return filename, offset

    def is_package(self, name):
        """
        Check if the given name refers to a package entry. Used by PyiFrozenImporter at runtime.
        """
        entry = self.toc.get(name)
        if entry is None:
            return False
        typecode, entry_offset, entry_length = entry
        return typecode in (PYZ_ITEM_PKG, PYZ_ITEM_NSPKG)

    def is_pep420_namespace_package(self, name):
        """
        Check if the given name refers to a namespace package entry. Used by PyiFrozenImporter at runtime.
        """
        entry = self.toc.get(name)
        if entry is None:
            return False
        typecode, entry_offset, entry_length = entry
        return typecode == PYZ_ITEM_NSPKG

    def extract(self, name, raw=False):
        """
        Extract data from entry with the given name.

        If the entry belongs to a module or a package, the data is loaded (unmarshaled) into code object. To retrieve
        raw data, set `raw` flag to True.
        """
        # Look up entry
        entry = self.toc.get(name)
        if entry is None:
            return None
        typecode, entry_offset, entry_length = entry

        # Read data blob
        try:
            with open(self._filename, "rb") as fp:
                fp.seek(self._start_offset + entry_offset)
                obj = fp.read(entry_length)
        except FileNotFoundError:
            # We open the archive file each time we need to read from it, to avoid locking the file by keeping it open.
            # This allows executable to be deleted or moved (renamed) while it is running, which is useful in certain
            # scenarios (e.g., automatic update that replaces the executable). The caveat is that once the executable is
            # renamed, we cannot read from its embedded PYZ archive anymore. In such case, exit with informative
            # message.
            raise SystemExit(
                f"{self._filename} appears to have been moved or deleted since this application was launched. "
                "Continouation from this state is impossible. Exiting now."
            )

        try:
            if self.cipher:
                obj = self.cipher.decrypt(obj)
            obj = zlib.decompress(obj)
            if typecode in (PYZ_ITEM_MODULE, PYZ_ITEM_PKG, PYZ_ITEM_NSPKG) and not raw:
                obj = marshal.loads(obj)
        except EOFError as e:
            raise ImportError(f"Failed to unmarshal PYZ entry {name!r}!") from e

        return obj
