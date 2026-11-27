# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""What the commands that check a gpg signature share."""

import os


def gpg_keyring(gpg, tmp, public_key, key_file_name):
    """Make a gpg home of its own in ``tmp`` and write ``public_key`` there.

    Returns the gpg options that use that home, and the key file's path.
    The caller imports the key and verifies: commands judge the import
    differently.
    """
    home = os.path.join(tmp, 'gpghome')
    os.makedirs(home, mode=0o700, exist_ok=True)
    key_file = os.path.join(tmp, key_file_name)
    with open(key_file, 'w') as f:
        f.write(public_key)
    return [gpg, '--homedir', home, '--batch', '--no-autostart'], key_file
