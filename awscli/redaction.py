# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import base64
import binascii
import re
from collections.abc import Mapping

_REDACTIONS = []


def register_redaction(pattern, replacement):
    """Register a pattern whose matches are replaced in logs and history.

    :type pattern: str or re.Pattern
    :param pattern: The regular expression to match sensitive text with.

    :type replacement: str or callable
    :param replacement: The literal text to replace each match with, or a
        function that takes the match object and returns the replacement
        text.

    Patterns are applied in registration order, so a pattern also sees the
    replacements made by patterns registered before it.
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    if not callable(replacement):
        text = replacement

        # A function's return value is used as is, whereas re.sub would
        # interpret backslashes in a replacement string as escapes.
        def replacement(match):
            return text

    _REDACTIONS.append((pattern, replacement))


def redact(value):
    """Return ``value`` with every registered pattern redacted.

    Strings and bytes are redacted, including those nested in lists, tuples,
    and mappings. Bytes are matched as UTF-8, and any bytes that aren't valid
    UTF-8 are preserved. Other values are returned unchanged.
    """
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, (bytes, bytearray)):
        # surrogateescape round-trips bytes that aren't valid UTF-8.
        text = value.decode('utf-8', 'surrogateescape')
        redacted = _redact_text(text).encode('utf-8', 'surrogateescape')
        return type(value)(redacted)
    if isinstance(value, (list, tuple)):
        items = [redact(item) for item in value]
        return items if isinstance(value, list) else tuple(items)
    if isinstance(value, Mapping):
        return {key: redact(item) for key, item in value.items()}
    return value


def _redact_text(text):
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


# PEM private keys.
_PRIVATE_KEY_PATTERN = re.compile(
    r'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'
    r'.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)',
    re.DOTALL,
)
_REDACTED_PRIVATE_KEY = '<redacted private key>'


def _redact_base64_private_key(match):
    # Only redact PEM data containing a private key, not e.g. certificates.
    encoded = match.group(0)
    try:
        decoded = base64.b64decode(encoded[: len(encoded) // 4 * 4])
    except binascii.Error:
        return encoded
    if _PRIVATE_KEY_PATTERN.search(decoded.decode('latin-1')):
        return _REDACTED_PRIVATE_KEY
    return encoded


register_redaction(_PRIVATE_KEY_PATTERN, _REDACTED_PRIVATE_KEY)

# Base64 encoded PEM data, such as blob parameters read with fileb://.
# "LS0tLS1CRUdJTi" is the base64 encoding of "-----BEGIN".
register_redaction(
    r'(?<![A-Za-z0-9+/])LS0tLS1CRUdJTi[A-Za-z0-9+/]*={0,2}',
    _redact_base64_private_key,
)
