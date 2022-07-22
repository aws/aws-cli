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
    """
    Returns a single or double quote character, whichever appears first in the
    given string. None is returned if the given string doesn't have a single or
    double quote character.
    """
    quote_char = None
    for ch in part:
        if ch in ('"', "'"):
            quote_char = ch
            break
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


def is_document_type(shape):
    """Check if shape is a document type"""
    return getattr(shape, 'is_document_type', False)


def is_document_type_container(shape):
    """Check if the shape is a document type or wraps document types

    This is helpful to determine if a shape purely deals with document types
    whether the shape is a document type or it is lists or maps whose base
    values are document types.
    """
    if not shape:
        return False
    recording_visitor = ShapeRecordingVisitor()
    ShapeWalker().walk(shape, recording_visitor)
    end_shape = recording_visitor.visited.pop()
    if not is_document_type(end_shape):
        return False
    for shape in recording_visitor.visited:
        if shape.type_name not in ['list', 'map']:
            return False
    return True


def operation_uses_document_types(operation_model):
    """Check if document types are ever used in the operation"""
    recording_visitor = ShapeRecordingVisitor()
    walker = ShapeWalker()
    walker.walk(operation_model.input_shape, recording_visitor)
    walker.walk(operation_model.output_shape, recording_visitor)
    for visited_shape in recording_visitor.visited:
        if is_document_type(visited_shape):
            return True
    return False


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


class ShapeWalker(object):
    def walk(self, shape, visitor):
        """Walk through and visit shapes for introspection

        :type shape: botocore.model.Shape
        :param shape: Shape to walk

        :type visitor: BaseShapeVisitor
        :param visitor: The visitor to call when walking a shape
        """

        if shape is None:
            return
        stack = []
        return self._walk(shape, visitor, stack)

    def _walk(self, shape, visitor, stack):
        if shape.name in stack:
            return
        stack.append(shape.name)
        getattr(self, '_walk_%s' % shape.type_name, self._default_scalar_walk)(
            shape, visitor, stack
        )
        stack.pop()

    def _walk_structure(self, shape, visitor, stack):
        self._do_shape_visit(shape, visitor)
        for _, member_shape in shape.members.items():
            self._walk(member_shape, visitor, stack)

    def _walk_list(self, shape, visitor, stack):
        self._do_shape_visit(shape, visitor)
        self._walk(shape.member, visitor, stack)

    def _walk_map(self, shape, visitor, stack):
        self._do_shape_visit(shape, visitor)
        self._walk(shape.value, visitor, stack)

    def _default_scalar_walk(self, shape, visitor, stack):
        self._do_shape_visit(shape, visitor)

    def _do_shape_visit(self, shape, visitor):
        visitor.visit_shape(shape)


class BaseShapeVisitor(object):
    """Visit shape encountered by ShapeWalker"""
    def visit_shape(self, shape):
        pass


class ShapeRecordingVisitor(BaseShapeVisitor):
    """Record shapes visited by ShapeWalker"""
    def __init__(self):
        self.visited = []

    def visit_shape(self, shape):
        self.visited.append(shape)
