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
import signal
import datetime
import contextlib
import os
import sys
import subprocess

from awscli.compat import six
from awscli.compat import get_binary_stdout
from awscli.compat import get_popen_kwargs_for_pager_cmd


def split_on_commas(value):
    if not any(char in value for char in ['"', '\\', "'", ']', '[']):
        # No quotes or escaping, just use a simple split.
        return value.split(',')
    elif not any(char in value for char in ['"', "'", '[', ']']):
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
        # Find the first quote
        quote_char = _find_quote_char_in_part(part)

        # Find an opening list bracket
        list_start = part.find('=[')

        if list_start >= 0 and value.find(']') != -1 and \
           (quote_char is None or part.find(quote_char) > list_start):
            # This is a list, eat all the items until the end
            if ']' in part:
                # Short circuit for only one item
                new_chunk = part
            else:
                new_chunk = _eat_items(value, iter_parts, part, ']')
            list_items = _split_with_quotes(new_chunk[list_start + 2:-1])
            new_chunk = new_chunk[:list_start + 1] + ','.join(list_items)
            new_parts.append(new_chunk)
            continue
        elif quote_char is None:
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
        new_chunk = _eat_items(value, iter_parts, part, quote_char, quote_char)
        new_parts.append(new_chunk)
    return new_parts


def _eat_items(value, iter_parts, part, end_char, replace_char=''):
    """
    Eat items from an iterator, optionally replacing characters with
    a blank and stopping when the end_char has been reached.
    """
    current = part
    chunks = [current.replace(replace_char, '')]
    while True:
        try:
            current = six.advance_iterator(iter_parts)
        except StopIteration:
            raise ValueError(value)
        chunks.append(current.replace(replace_char, ''))
        if current.endswith(end_char):
            break
    return ','.join(chunks)


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


def find_service_and_method_in_event_name(event_name):
    """
    Grabs the service id and the operation name from an event name.
    This is making the assumption that the event name is in the form
    event.service.operation.
    """
    split_event = event_name.split('.')[1:]
    service_name = None
    if len(split_event) > 0:
        service_name = split_event[0]

    operation_name = None
    if len(split_event) > 1:
        operation_name = split_event[1]
    return service_name, operation_name


def json_encoder(obj):
    """JSON encoder that formats datetimes as ISO8601 format."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return obj


@contextlib.contextmanager
def ignore_ctrl_c():
    original = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, original)


def emit_top_level_args_parsed_event(session, args):
    session.emit(
        'top-level-args-parsed', parsed_args=args, session=session)


def is_a_tty():
    try:
        return os.isatty(sys.stdout.fileno())
    except Exception as e:
        return False


class OutputStreamFactory(object):
    def __init__(self, popen=None):
        self._popen = popen
        if popen is None:
            self._popen = subprocess.Popen

    @contextlib.contextmanager
    def get_pager_stream(self, preferred_pager=None):
        popen_kwargs = self._get_process_pager_kwargs(preferred_pager)
        try:
            process = self._popen(**popen_kwargs)
            yield process.stdin
        except IOError:
            # Ignore IOError since this can commonly be raised when a pager
            # is closed abruptly and causes a broken pipe.
            pass
        finally:
            process.communicate()

    @contextlib.contextmanager
    def get_stdout_stream(self):
        yield get_binary_stdout()

    def _get_process_pager_kwargs(self, pager_cmd):
        kwargs = get_popen_kwargs_for_pager_cmd(pager_cmd)
        kwargs['stdin'] = subprocess.PIPE
        return kwargs


def write_exception(ex, outfile):
    outfile.write("\n")
    outfile.write(six.text_type(ex))
    outfile.write("\n")
