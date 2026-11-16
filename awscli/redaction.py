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
_REDACTED_KEYS = {}


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


def register_redacted_key(name, replacement):
    """Register a mapping key whose text values are replaced.

    :type name: str
    :param name: The key to redact the values of, matched without regard
        to case, such as a response field or a request header name.

    :type replacement: str
    :param replacement: The literal text to replace each value with.

    Patterns only see a mapping's values, not its keys, so a secret kept
    under a known key, as in a parsed response or a dict of headers, needs
    this as well as a pattern.
    """
    _REDACTED_KEYS[name.lower()] = replacement


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
        return {key: _redact_item(key, item) for key, item in value.items()}
    return value


def _redact_item(key, item):
    if isinstance(key, str) and isinstance(item, (str, bytes, bytearray)):
        replacement = _REDACTED_KEYS.get(key.lower())
        if replacement is not None:
            if isinstance(item, str):
                return replacement
            return type(item)(replacement.encode('utf-8'))
    return redact(item)


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

# Temporary AWS credentials, as in the responses of the AWS STS AssumeRole*,
# GetSessionToken and GetFederationToken operations (XML), of IAM Identity
# Center GetRoleCredentials (JSON, camel case) and of Amazon Cognito
# GetCredentialsForIdentity (SecretKey), and the session token of a signed
# request (the SigV4 header or the SigV2 parameter). The access key ID and the
# expiration aren't secret and stay visible.
_REDACTED_CREDENTIAL = '<redacted credential>'
_SECRET_CREDENTIAL_FIELDS = ('SecretAccessKey', 'SecretKey', 'SessionToken')
_SECURITY_TOKEN_NAMES = ('X-Amz-Security-Token', 'SecurityToken')
_FIELDS = '|'.join(_SECRET_CREDENTIAL_FIELDS)
_TOKENS = '|'.join(_SECURITY_TOKEN_NAMES)
# A quoted value, up to its closing quote, which may be escaped when the
# text is itself inside a JSON string.
_QUOTED_VALUE = r'[^"\']+?(?=\\?["\'])'


def _keep_prefix(match):
    # Redacting text twice gives the same text as redacting it once.
    return match.group(1) + _REDACTED_CREDENTIAL


# An XML element, such as <SessionToken>...</SessionToken>, also with a
# namespace prefix or attributes.
register_redaction(
    re.compile(rf'(<(?:\w+:)?(?:{_FIELDS})(?:\s[^>]*)?>)[^<]+', re.IGNORECASE),
    _keep_prefix,
)
# A quoted key and value, as in JSON or a Python dict's repr, and the
# session token header in a dict of headers.
register_redaction(
    re.compile(
        rf'(\\?["\'](?:{_FIELDS}|{_TOKENS})\\?["\']\s*:\s*'
        rf'b?\\?["\']){_QUOTED_VALUE}',
        re.IGNORECASE,
    ),
    _keep_prefix,
)
# The session token in the signature's canonical request or string to
# sign, a presigned URL's query string, or a SigV2 form body.
register_redaction(
    re.compile(rf'((?:{_TOKENS})[:=])[^\s"\',&}}\\<]+', re.IGNORECASE),
    _keep_prefix,
)
for _name in _SECRET_CREDENTIAL_FIELDS + _SECURITY_TOKEN_NAMES:
    register_redacted_key(_name, _REDACTED_CREDENTIAL)
