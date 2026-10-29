# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Central output caps for aggregating read commands.

Output is bounded to keep responses manageable: row and series counts are capped
and oversized free-text fields (such as a Logs Insights ``@message``) are
truncated. Every clamp is recorded so the caller can see that the result was
trimmed rather than silently losing data.
"""

from __future__ import annotations

from typing import Any

# Default width an individual free-text field is truncated to. Full log lines
# can be many kilobytes; 2000 chars keeps the head (where the error usually is)
# while preventing one row from dominating the response.
DEFAULT_MESSAGE_MAX_CHARS = 2000
_TRUNCATION_SUFFIX = "...[truncated]"


def truncate_field(value: Any, max_chars: int) -> tuple[Any, bool]:
    """Truncate a string to ``max_chars`` (keeping the head).

    Returns ``(value, truncated)``. Non-strings and ``max_chars <= 0`` pass
    through untouched so callers can disable truncation.

    Note: when *max_chars* is smaller than the suffix length (14 chars), the
    returned string may exceed *max_chars*. This is intentional; practical
    defaults are 2000+.
    """
    if max_chars <= 0 or not isinstance(value, str) or len(value) <= max_chars:
        return value, False
    head = value[: max(0, max_chars - len(_TRUNCATION_SUFFIX))]
    return head + _TRUNCATION_SUFFIX, True


def cap_series(items: list[Any], max_count: int) -> tuple[list[Any], int]:
    """Cap a list to ``max_count`` entries.

    Returns ``(kept, dropped)`` where ``dropped`` is how many were removed, so
    the caller can report the clamp in ``clamps``/``guidance``.
    """
    if max_count < 0 or len(items) <= max_count:
        return items, 0
    return items[:max_count], len(items) - max_count
