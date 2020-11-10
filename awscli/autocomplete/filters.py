# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from collections import namedtuple


def fuzzy_filter(prefix, completions):
    # To filter we transform string to regex in such a way:
    #
    # "rmt" -> /r.*?m.*?t/
    #
    # and search for matching in all the strings. All the matches we
    # sort in such a way that shortest and the the closest to the beginning
    # match part coming first. It means that the first completion will
    # be a string where distance between matching letters as small
    # as possible and the first letter is as close to the beginning as possible

    if prefix and completions:
        fuzzy_matches = []
        # lookahead regex to manage overlapping matches
        pattern = ".*?".join(map(re.escape, prefix))
        pattern = f'(?=({pattern}))'
        regex = re.compile(pattern, re.IGNORECASE)
        for completion in completions:
            name = completion.display_text or completion.name
            matches = list(regex.finditer(name))
            if matches:
                # Prefer the match, closest to the left, then shortest.
                best = min(matches, key=lambda m: (m.start(),
                                                   len(m.group(1))))
                fuzzy_matches.append(_FuzzyMatch(
                    len(best.group(1)),
                    best.start(),
                    completion)
                )
        return [x for _, _, x in sorted(
                    fuzzy_matches,
                    key=lambda match: (
                        match.match_length, match.start_pos,
                        match.completion.display_text,
                        match.completion.name)
                )]
    return completions


def startswith_filter(prefix, completions):
    return [
        completion for completion in completions
        if (completion.display_text or completion.name).startswith(prefix)
    ]


_FuzzyMatch = namedtuple('_FuzzyMatch', 'match_length start_pos completion')
