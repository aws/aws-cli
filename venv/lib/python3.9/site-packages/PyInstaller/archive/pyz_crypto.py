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

import os

from PyInstaller import log as logging

BLOCK_SIZE = 16
logger = logging.getLogger(__name__)


class PyiBlockCipher:
    """
    This class is used only to encrypt Python modules.
    """
    def __init__(self, key=None):
        logger.log(
            logging.DEPRECATION,
            "Bytecode encryption will be removed in PyInstaller v6. Please remove cipher and block_cipher parameters "
            "from your spec file to avoid breakages on upgrade. For the rationale/alternatives see "
            "https://github.com/pyinstaller/pyinstaller/pull/6999"
        )
        assert type(key) is str
        if len(key) > BLOCK_SIZE:
            self.key = key[0:BLOCK_SIZE]
        else:
            self.key = key.zfill(BLOCK_SIZE)
        assert len(self.key) == BLOCK_SIZE

        import tinyaes
        self._aesmod = tinyaes

    def encrypt(self, data):
        iv = os.urandom(BLOCK_SIZE)
        return iv + self.__create_cipher(iv).CTR_xcrypt_buffer(data)

    def __create_cipher(self, iv):
        # The 'AES' class is stateful, and this factory method is used to re-initialize the block cipher class with
        # each call to xcrypt().
        return self._aesmod.AES(self.key.encode(), iv)
