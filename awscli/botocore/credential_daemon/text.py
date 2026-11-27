# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Text from the credential daemon or the config, made safe for a terminal."""

import re
import unicodedata

# C0 and C1 control characters, which include ESC.
_CONTROL_CHARACTERS = re.compile(r'[\x00-\x1f\x7f-\x9f]')
# Kept as a space, so the words on either side don't run together.
_SPACE_CHARACTERS = '\t\n\r'
# Unicode categories dropped too: Cf holds the bidi overrides and isolates
# (U+202A-202E, U+2066-2069) and zero-width characters (U+200B-200D),
# which reorder or hide what the terminal shows. Zl and Zp (U+2028,
# U+2029) break the line, so they become spaces.
_FORMAT_CATEGORY = 'Cf'
_SEPARATOR_CATEGORIES = ('Zl', 'Zp')


def strip_control_characters(text):
    """Remove control characters from text the credential daemon sent, before
    printing.

    Escape sequences in it could otherwise rewrite what the terminal
    shows, such as a prompt, and bidi or zero-width characters could
    make a command read differently from what it copies as. Tabs and
    line breaks become spaces.
    """
    if not isinstance(text, str):
        return text
    text = _CONTROL_CHARACTERS.sub(
        lambda m: ' ' if m.group() in _SPACE_CHARACTERS else '', text
    )
    if text.isascii():
        return text
    return ''.join(_strip_format_character(c) for c in text)


def _strip_format_character(character):
    category = unicodedata.category(character)
    if category == _FORMAT_CATEGORY:
        return ''
    if category in _SEPARATOR_CATEGORIES:
        return ' '
    return character


def _seconds(timeout):
    if timeout == int(timeout):
        timeout = int(timeout)
    return f'{timeout}-second'


def _os_error(error):
    # The OS's text for the error, without Python's "[Errno n]" prefix.
    text = error.strerror or str(error) or type(error).__name__
    return strip_control_characters(text)


def end_sentence(message):
    """``message`` without trailing space, ending in ``.``, ``!`` or ``?``."""
    message = message.rstrip()
    if not message.endswith(('.', '!', '?')):
        message += '.'
    return message
