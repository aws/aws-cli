# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Where ``aws login``, ``aws signup`` and ``aws logout`` keep sessions.

A backend owns one place a session can be kept. The commands do the steps
every backend shares: they resolve the profile and region before the
browser opens, make the one write to the config file, and report the
result. A backend does the rest.
"""

from collections import namedtuple

# What the command resolved before the sign-in starts. ``choice`` is where
# the session goes (a ``StorageChoice``). ``leaving`` is what the profile
# leaves in the backend that held its session until now (see
# ``SignInBackend.leave``), or None.
SignInRequest = namedtuple(
    'SignInRequest',
    [
        'profile_name',
        'region',
        'sign_in_type',
        'is_new_profile',
        'parsed_args',
        'parsed_globals',
        'choice',
        'leaving',
    ],
    defaults=(None, None),
)

# What a backend's sign-in returns. ``ok`` is False when the sign-in
# stopped without signing in; the command then exits with ``exit_code``
# (None is 0) and writes nothing. Otherwise ``profile_values`` are the
# keys to save to the profile, and ``access_token`` is the token the
# sign-in returned, or None if the backend doesn't hand it out.
SignInResult = namedtuple(
    'SignInResult',
    ['ok', 'exit_code', 'profile_values', 'access_token'],
    defaults=(None, None),
)

# What a backend's sign-out returns: whether nothing was left behind, and,
# for ALL_SESSIONS, whether there was nothing to sign out.
SignOutResult = namedtuple('SignOutResult', ['ok', 'empty'])

# Passed to ``sessions()`` for ``aws logout --all``: every session the
# backend holds, for every profile.
ALL_SESSIONS = object()


class SignInBackend:
    """One place ``aws login`` can keep a session."""

    def check(self, profile_name, command):
        """Refuse, before any prompt or browser, a sign-in this backend
        can't keep for the profile. ``command`` is the command's name, for
        the message."""

    def holds(self, profile_name, before):
        """Whether the profile's session is in this backend. ``before`` is
        the profile's config before the sign-in."""
        return False

    def leave(self, profile_name, before):
        """What a sign-in into another backend does with the profile's
        session here, as a ``Leaving``. Called only when ``holds`` is
        True."""
        raise NotImplementedError('leave')

    def sign_in(self, request):
        """Sign in for ``request`` and keep the session.

        Returns a ``SignInResult``. Don't write the config file: the
        command writes ``profile_values`` once, with the region.
        """
        raise NotImplementedError('sign_in')

    def write_failed(self, request):
        """Called when the profile write fails after a sign-in that
        returned ok. Undo anything that is no use without the write; the
        command re-raises the error after it."""

    def after_write(self, request, result):
        """Called after the profile is written. Say what changed.

        When the session moved from another backend, also call
        ``request.leaving``'s ``note``, ``release`` and ``after_summary`` at
        their places in the output.
        """


class Leaving:
    """What a profile leaves in the backend its session moves out of, for
    one sign-in.

    ``values_to_clear`` goes in the sign-in's one profile write. The new
    backend's ``after_write`` calls the rest, only after the write
    succeeded: ``note`` before its storage line, ``release`` to clean up
    (it returns lines for the new backend's summary), and
    ``after_summary`` after the summary.
    """

    # 1 if the clean-up left something behind, else None.
    exit_code = None

    def values_to_clear(self):
        """Profile values the write removes (set to None)."""
        return {}

    def note(self):
        """Say what the write removed."""

    def release(self):
        """Clean up what's left now that the profile is written. Returns
        lines for the new backend's summary."""
        return []

    def after_summary(self):
        """Anything left to say or ask once the summary is out."""


class SignOutBackend:
    """One place ``aws logout`` can sign sessions out of."""

    def sessions(self, profile):
        """The targets to pass to ``sign_out`` for ``profile``, a profile
        name or ALL_SESSIONS. Return an empty list if the backend holds
        nothing for it."""
        raise NotImplementedError('sessions')

    def sign_out(self, target):
        """Sign out one target from ``sessions`` and say what was removed.
        Returns a ``SignOutResult``."""
        raise NotImplementedError('sign_out')
