# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import csv

import six


def split_on_commas(value):
    if '"' not in value and '\\' not in value and "'" not in value:
        # No quotes or escaping, just use a simple split.
        return value.split(',')
    elif '"' not in value and "'" not in value:
        # Simple escaping, let the csv module handle it.
        return list(csv.reader(six.StringIO(value), escapechar='\\'))[0]
    else:
        # If there's quotes for the values, we have to handle this
        # ourselves.
        return _split_with_quotes(value)


def _split_with_quotes(value):
    try:
        parts = list(csv.reader(six.StringIO(value), escapechar='\\'))[0]
    except csv.Error:
        raise ValueError("Bad csv value: %s" % value)
    iter_parts = iter(parts)
    new_parts = []
    for part in iter_parts:
        quote_char = _find_quote_char_in_part(part)
        if quote_char is None:
            new_parts.append(part)
            continue
        elif part.count(quote_char) == 2:
            # Starting and ending quote are in this part.
            # While it's not needed right now, this will
            # break down if we ever need to escape quotes while
            # quoting a value.
            new_parts.append(part.replace(quote_char, ''))
            continue
        # Now that we've found a starting quote char, we
        # need to combine the parts until we encounter an end quote.
        current = part
        chunks = [current.replace(quote_char, '')]
        while True:
            try:
                current = six.advance_iterator(iter_parts)
            except StopIteration:
                raise ValueError(value)
            chunks.append(current.replace(quote_char, ''))
            if quote_char in current:
                break
        new_chunk = ','.join(chunks)
        new_parts.append(new_chunk)
    return new_parts


def _find_quote_char_in_part(part):
    if '"' not in part and "'" not in part:
        return
    quote_char = None
    double_quote = part.find('"')
    single_quote = part.find("'")
    if double_quote >= 0 and single_quote == -1:
        quote_char = '"'
    elif single_quote >= 0 and double_quote == -1:
        quote_char = "'"
    elif double_quote < single_quote:
        quote_char = '"'
    elif single_quote < double_quote:
        quote_char = "'"
    return quote_char
