# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The macOS check that the credential daemon's process is the signed
credential daemon."""

import logging
import sys

from botocore.credential_daemon.discovery import _untrusted
from botocore.credential_daemon.text import _os_error, strip_control_characters
from botocore.credential_daemon.trust import _SOL_LOCAL, shown_socket

# One logger name for the package, as before the split, so --debug
# output is the same.
logger = logging.getLogger('botocore.credential_daemon')


# macOS: LOCAL_PEERTOKEN from <sys/un.h>, and the size of audit_token_t
# (eight 32-bit words). The audit token names the peer process instance,
# so unlike a pid it can't be reused by another process between the
# lookup and the check.
_LOCAL_PEERTOKEN = 6
_AUDIT_TOKEN_SIZE = 32
# The Apple Developer Team ID aws-credential-daemon's macOS packages and app
# are signed with, and the app's bundle identifier. Both match the v0.1.0
# .pkg.
CREDENTIAL_DAEMON_TEAM_ID = '94KV3E626L'
CREDENTIAL_DAEMON_PACKAGE_ID = 'com.amazon.aws.credsd.daemon'
# The code requirement the process serving the socket must meet on macOS,
# before the CLI sends it a secret: an Apple-anchored Developer ID
# Application certificate for CREDENTIAL_DAEMON_TEAM_ID, and the daemon's
# bundle identifier. It's the designated requirement the v0.1.0
# aws-credential-daemon release carries (`codesign -d -r-`). The credential
# daemon hasn't committed to it, so it changes if a later release is signed
# differently.
CREDENTIAL_DAEMON_CODE_REQUIREMENT = (
    f'identifier "{CREDENTIAL_DAEMON_PACKAGE_ID}" and anchor apple generic '
    'and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ '
    'and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ '
    f'and certificate leaf[subject.OU] = "{CREDENTIAL_DAEMON_TEAM_ID}"'
)
_SECURITY_FRAMEWORK = '/System/Library/Frameworks/Security.framework/Security'
_CORE_FOUNDATION = (
    '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
)
_K_CF_STRING_ENCODING_UTF8 = 0x08000100
_K_SEC_CS_DEFAULT_FLAGS = 0
# The OSStatus codes from <Security/CSCommon.h> that mean the peer's code
# was checked and isn't the signed credential daemon: the requirement
# failed (errSecCSReqFailed), the code isn't signed (errSecCSUnsigned), its
# signature is broken (errSecCSSignatureFailed), or the running process is
# no longer valid (errSecCSGuestInvalid). Any other non-zero code means the
# CLI couldn't check it. Both refuse.
_NOT_THE_SIGNED_DAEMON = frozenset((-67050, -67062, -67061, -67063))


def checks_code_signature():
    """Whether ``SocketChecks.FULL`` connections check the peer's code
    signature too (``check_code_signature``): on macOS only, at every
    socket."""
    return sys.platform == 'darwin'


def check_code_signature(sock, path, given=None):
    """Check that the process serving ``sock`` is the signed credential
    daemon, on macOS.

    The peer's audit token (``LOCAL_PEERTOKEN``) names the process on the
    other end of this connection. Security.framework looks up its code and
    checks it, and its signature, against
    ``CREDENTIAL_DAEMON_CODE_REQUIREMENT``. This is the only check that tells
    the real daemon from another program serving the same socket.

    Fails closed: if the token can't be read, Security.framework can't be
    loaded or called, or the check returns any non-zero OSStatus, it raises
    ``CredentialDaemonUntrustedSocketError``. ``path`` is the resolved
    path and ``given`` the one before links were resolved, for the message
    (see ``shown_socket``).
    """
    shown = shown_socket(path if given is None else given, path)
    try:
        token = _peer_audit_token(sock)
    except (OSError, ValueError) as e:
        reason = _os_error(e) if isinstance(e, OSError) else str(e)
        raise _untrusted(
            shown, f'the CLI couldn\'t read which process serves it: {reason}'
        ) from e
    try:
        status = _code_signature_status(
            token, CREDENTIAL_DAEMON_CODE_REQUIREMENT
        )
    except Exception as e:
        # ctypes and Security.framework failures alike: a missing library
        # or symbol, a bad argument, a NULL result.
        logger.debug('Code signature check failed', exc_info=True)
        raise _untrusted(
            shown,
            'the CLI couldn\'t check the credential daemon\'s signature: '
            f'{strip_control_characters(str(e)) or type(e).__name__}',
        ) from e
    if status in _NOT_THE_SIGNED_DAEMON:
        raise _untrusted(
            shown,
            'the process serving it isn\'t the signed credential daemon '
            f'(OSStatus {status}). Install the signed release with "aws '
            'configure credential-daemon install"',
        )
    if status != 0:
        raise _untrusted(
            shown,
            'the CLI couldn\'t check the credential daemon\'s signature '
            f'(OSStatus {status})',
        )


def _peer_audit_token(sock):
    """The audit token of the process on the other end of ``sock``
    (macOS)."""
    token = sock.getsockopt(_SOL_LOCAL, _LOCAL_PEERTOKEN, _AUDIT_TOKEN_SIZE)
    if len(token) != _AUDIT_TOKEN_SIZE:
        raise ValueError(
            f'its audit token is {len(token)} bytes, not {_AUDIT_TOKEN_SIZE}'
        )
    return token


# Security.framework and CoreFoundation, loaded on first use and kept.
_code_signing = None


def _code_signature_status(token, requirement):
    """The OSStatus of checking the process with audit ``token`` against
    the code ``requirement``, 0 if it meets it."""
    global _code_signing
    if _code_signing is None:
        _code_signing = _CodeSigning.load()
    return _code_signing.check(token, requirement)


class _CodeSigning:
    """The few Security.framework and CoreFoundation calls the code
    signature check makes, through ``ctypes`` (standard library only).

    ``load`` takes the library loader and the data symbol lookup, so tests
    can give it fakes.
    """

    def __init__(
        self, cf, sec, guest_attribute_audit, key_callbacks, value_callbacks
    ):
        self._cf = cf
        self._sec = sec
        self._audit_key = guest_attribute_audit
        self._key_callbacks = key_callbacks
        self._value_callbacks = value_callbacks

    @classmethod
    def load(cls, cdll=None, in_dll=None):
        # Imported here: only macOS uses it, so other platforms skip the cost.
        import ctypes

        if cdll is None:
            cdll = ctypes.CDLL
        if in_dll is None:
            in_dll = _in_dll
        cf = cdll(_CORE_FOUNDATION)
        sec = cdll(_SECURITY_FRAMEWORK)
        p = ctypes.c_void_p
        status = ctypes.c_int32
        flags = ctypes.c_uint32
        signatures = {
            (cf, 'CFDataCreate'): (p, [p, ctypes.c_char_p, ctypes.c_long]),
            (cf, 'CFStringCreateWithCString'): (
                p,
                [p, ctypes.c_char_p, ctypes.c_uint32],
            ),
            (cf, 'CFDictionaryCreate'): (
                p,
                [p, ctypes.POINTER(p), ctypes.POINTER(p), ctypes.c_long, p, p],
            ),
            (cf, 'CFRelease'): (None, [p]),
            (sec, 'SecCodeCopyGuestWithAttributes'): (
                status,
                [p, p, flags, ctypes.POINTER(p)],
            ),
            (sec, 'SecRequirementCreateWithString'): (
                status,
                [p, flags, ctypes.POINTER(p)],
            ),
            (sec, 'SecCodeCheckValidity'): (status, [p, flags, p]),
        }
        for (lib, name), (restype, argtypes) in signatures.items():
            function = getattr(lib, name)
            function.restype = restype
            function.argtypes = argtypes
        audit_key = in_dll(ctypes.c_void_p, sec, 'kSecGuestAttributeAudit')
        if not audit_key:
            raise ValueError('kSecGuestAttributeAudit is NULL')
        return cls(
            cf,
            sec,
            audit_key,
            in_dll(None, cf, 'kCFTypeDictionaryKeyCallBacks'),
            in_dll(None, cf, 'kCFTypeDictionaryValueCallBacks'),
        )

    def check(self, token, requirement):
        # Imported here: only macOS uses it, so other platforms skip the cost.
        import ctypes

        cf, sec = self._cf, self._sec
        made = []

        def keep(ref, what):
            if not ref:
                raise ValueError(f'{what} returned NULL')
            made.append(ref)
            return ref

        try:
            data = keep(
                cf.CFDataCreate(None, token, len(token)), 'CFDataCreate'
            )
            keys = (ctypes.c_void_p * 1)(self._audit_key)
            values = (ctypes.c_void_p * 1)(data)
            attributes = keep(
                cf.CFDictionaryCreate(
                    None,
                    keys,
                    values,
                    1,
                    self._key_callbacks,
                    self._value_callbacks,
                ),
                'CFDictionaryCreate',
            )
            code = ctypes.c_void_p()
            status = sec.SecCodeCopyGuestWithAttributes(
                None, attributes, _K_SEC_CS_DEFAULT_FLAGS, ctypes.byref(code)
            )
            if status != 0:
                return status
            keep(code.value, 'SecCodeCopyGuestWithAttributes')
            text = keep(
                cf.CFStringCreateWithCString(
                    None,
                    requirement.encode('utf-8'),
                    _K_CF_STRING_ENCODING_UTF8,
                ),
                'CFStringCreateWithCString',
            )
            req = ctypes.c_void_p()
            status = sec.SecRequirementCreateWithString(
                text, _K_SEC_CS_DEFAULT_FLAGS, ctypes.byref(req)
            )
            if status != 0:
                return status
            keep(req.value, 'SecRequirementCreateWithString')
            return sec.SecCodeCheckValidity(code, _K_SEC_CS_DEFAULT_FLAGS, req)
        finally:
            for ref in reversed(made):
                cf.CFRelease(ref)


def _in_dll(ctype, lib, name):
    """A data symbol from ``lib``: the pointer it holds for ``ctype``
    ``c_void_p``, or its address when ``ctype`` is None (for structs such
    as CoreFoundation's callbacks)."""
    # Imported here: only macOS uses it, so other platforms skip the cost.
    import ctypes

    if ctype is None:
        return ctypes.addressof(ctypes.c_byte.in_dll(lib, name))
    return ctype.in_dll(lib, name).value
