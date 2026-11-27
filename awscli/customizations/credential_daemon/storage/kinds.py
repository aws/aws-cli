# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The kinds of credentials a profile can store."""

from enum import Enum


class CredentialKind(Enum):
    """What a storage question is about. Never written or shown."""

    SESSION = 'session'
    STATIC_KEYS = 'keys'
