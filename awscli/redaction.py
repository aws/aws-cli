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

import re
from collections.abc import Mapping

_REDACTIONS = []


def register_redaction(pattern, replacement):
    """Register a pattern whose matches are replaced in logs and history.

    :type pattern: str or re.Pattern
    :param pattern: The regular expression to match sensitive text with.

    :type replacement: str
    :param replacement: The text to replace each match with.
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    _REDACTIONS.append((pattern, replacement))


def redact(value):
    """Return ``value`` with every registered pattern redacted.

    Strings and UTF-8 encoded bytes are redacted, including those nested in
    lists, tuples, and mappings. Other values, and values without a match,
    are returned unchanged.
    """
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, bytes):
        try:
            text = value.decode('utf-8')
        except UnicodeDecodeError:
            return value
        redacted = _redact_text(text)
        return value if redacted is text else redacted.encode('utf-8')
    if isinstance(value, (list, tuple)):
        items = [redact(item) for item in value]
        if all(new is old for new, old in zip(items, value)):
            return value
        return items if isinstance(value, list) else tuple(items)
    if isinstance(value, Mapping):
        items = {key: redact(item) for key, item in value.items()}
        if all(items[key] is item for key, item in value.items()):
            return value
        return items
    return value


def _redact_text(text):
    redacted = text
    for pattern, replacement in _REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    # Keep the original object when nothing matched.
    return text if redacted == text else redacted


# PEM private keys, e.g. passed inline to ``aws cloudfront sign
# --private-key``. An unterminated key is redacted up to the end of the text.
register_redaction(
    re.compile(
        r'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'
        r'.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)',
        re.DOTALL,
    ),
    '<redacted private key>',
)
