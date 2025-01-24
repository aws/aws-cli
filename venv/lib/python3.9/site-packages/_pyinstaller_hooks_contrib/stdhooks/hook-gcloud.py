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

from PyInstaller.utils.hooks import copy_metadata

# This hook was written for `gcloud` - https://pypi.org/project/gcloud
# Suppress package-not-found errors when the hook is triggered by `gcloud` namespace package from `gcloud-aio-*` and
# `gcloud-rest-*˙ dists (https://github.com/talkiq/gcloud-aio).
try:
    datas = copy_metadata('gcloud')
except Exception:
    pass
