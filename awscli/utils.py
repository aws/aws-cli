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
import re
import sys
from subprocess import Popen, PIPE
import logging

from awscli.compat import six
from awscli.compat import get_stdout_text_writer
from awscli.compat import get_popen_kwargs_for_pager_cmd
from awscli.compat import StringIO
from botocore.utils import resolve_imds_endpoint_mode
from botocore.utils import IMDSFetcher
from botocore.configprovider import BaseProvider

logger = logging.getLogger(__name__)


class PagerInitializationException(Exception):
    pass


class LazyStdin:
    def __init__(self, process):
        self._process = process
        self._stream = None

    def __getattr__(self, item):
        if self._stream is None:
            self._stream = self._process.initialize().stdin
        return getattr(self._stream, item)

    def flush(self):
        # if stream has not been created yet there is no reason to create it
        # just to call `flush`
        if self._stream is not None:
            return self._stream.flush()


class LazyPager:
    # Spin up a new process only in case it has been called or its stdin
    # has been called
    def __init__(self, popen, **kwargs):
        self._popen = popen
        self._popen_kwargs = kwargs
        self._process = None
        self.stdin = LazyStdin(self)

    def initialize(self):
        if self._process is None:
            self._process = self._do_popen()
        return self._process

    def __getattr__(self, item):
        return getattr(self.initialize(), item)

    def communicate(self, *args, **kwargs):
        # if pager process has not been created yet it means we didn't
        # write to its stdin and there is no reason to create it just
        # to call `communicate` so we can ignore this call
        if self._process is not None or args or kwargs:
            return getattr(self.initialize(), 'communicate')(*args, **kwargs)
        return None, None

    def _do_popen(self):
        try:
            return self._popen(**self._popen_kwargs)
        except FileNotFoundError as e:
            raise PagerInitializationException(e)


class IMDSRegionProvider(BaseProvider):
    def __init__(self, session, environ=None, fetcher=None):
        """Initialize IMDSRegionProvider.

        :type session: :class:`botocore.session.Session`
        :param session: The session is needed to look up configuration for
            how to contact the instance metadata service. Specifically the
            whether or not it should use the IMDS region at all, and if so how
            to configure the timeout and number of attempts to reach the
            service.

        :type environ: None or dict
        :param environ: A dictionary of environment variables to use. If
            ``None`` is the argument then ``os.environ`` will be used by
            default.

        :type fecther: :class:`botocore.utils.InstanceMetadataRegionFetcher`
        :param fetcher: The class to actually handle the fetching of the region
            from the IMDS. If not provided a default one will be created.
        """
        self._session = session
        if environ is None:
            environ = os.environ
        self._environ = environ
        self._fetcher = fetcher

    def provide(self):
        """Provide the region value from IMDS."""
        instance_region = self._get_instance_metadata_region()
        return instance_region

    def _get_instance_metadata_region(self):
        fetcher = self._get_fetcher()
        region = fetcher.retrieve_region()
        return region

    def _get_fetcher(self):
        if self._fetcher is None:
            self._fetcher = self._create_fetcher()
        return self._fetcher

    def _create_fetcher(self):
        metadata_timeout = self._session.get_config_variable(
            'metadata_service_timeout')
        metadata_num_attempts = self._session.get_config_variable(
            'metadata_service_num_attempts')
        imds_config = {
            'ec2_metadata_service_endpoint': self._session.get_config_variable(
                'ec2_metadata_service_endpoint'),
            'ec2_metadata_service_endpoint_mode': resolve_imds_endpoint_mode(
                self._session
            )
        }
        fetcher = InstanceMetadataRegionFetcher(
            timeout=metadata_timeout,
            num_attempts=metadata_num_attempts,
            env=self._environ,
            user_agent=self._session.user_agent(truncate=True),
            config=imds_config,
        )
        return fetcher


class InstanceMetadataRegionFetcher(IMDSFetcher):
    _URL_PATH = 'latest/meta-data/placement/availability-zone/'

    def retrieve_region(self):
        """Get the current region from the instance metadata service.

        :rvalue: str
        :returns: The region the current instance is running in or None
            if the instance metadata service cannot be contacted or does not
            give a valid response.

        :rtype: None or str
        :returns: Returns the region as a string if it is configured to use
            IMDS as a region source. Otherwise returns ``None``. It will also
            return ``None`` if it fails to get the region from IMDS due to
            exhausting its retries or not being able to connect.
        """
        try:
            region = self._get_region()
            return region
        except self._RETRIES_EXCEEDED_ERROR_CLS:
            logger.debug("Max number of attempts exceeded (%s) when "
                         "attempting to retrieve data from metadata service.",
                         self._num_attempts)
        return None

    def _get_region(self):
        token = self._fetch_metadata_token()
        response = self._get_request(
            url_path=self._URL_PATH,
            retry_func=self._default_retry,
            token=token
        )
        availability_zone = response.text
        region = availability_zone[:-1]
        return region


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


def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


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


def is_streaming_blob_type(shape):
    """Check if the shape is a streaming blob type."""
    return (shape and shape.type_name == 'blob' and
            shape.serialization.get('streaming', False))


def is_tagged_union_type(shape):
    """Check if the shape is a tagged union structure."""
    return getattr(shape, 'is_tagged_union', False)


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


def is_stdin_a_tty():
    try:
        return os.isatty(sys.stdin.fileno())
    except Exception as e:
        return False


class OutputStreamFactory(object):
    def __init__(self, session, popen=None, environ=None,
                 default_less_flags='FRX'):
        self._session = session
        self._popen = popen
        if popen is None:
            self._popen = Popen
        self._environ = environ
        if environ is None:
            self._environ = os.environ.copy()
        self._default_less_flags = default_less_flags

    def get_output_stream(self):
        pager = self._get_configured_pager()
        if is_a_tty() and pager:
            return self.get_pager_stream(pager)
        return self.get_stdout_stream()

    @contextlib.contextmanager
    def get_pager_stream(self, preferred_pager=None):
        if not preferred_pager:
            preferred_pager = self._get_configured_pager()
        popen_kwargs = self._get_process_pager_kwargs(preferred_pager)
        process = LazyPager(self._popen, **popen_kwargs)
        try:
            yield process.stdin
        except IOError:
            # Ignore IOError since this can commonly be raised when a pager
            # is closed abruptly and causes a broken pipe.
            pass
        finally:
            process.communicate()

    @contextlib.contextmanager
    def get_stdout_stream(self):
        yield get_stdout_text_writer()

    def _get_configured_pager(self):
        return self._session.get_component('config_store').get_config_variable(
            'pager'
        )

    def _get_process_pager_kwargs(self, pager_cmd):
        kwargs = get_popen_kwargs_for_pager_cmd(pager_cmd)
        kwargs['stdin'] = PIPE
        env = self._environ.copy()
        if 'LESS' not in env:
            env['LESS'] = self._default_less_flags
        kwargs['env'] = env
        kwargs['universal_newlines'] = True
        return kwargs


def write_exception(ex, outfile):
    outfile.write("\n")
    outfile.write(six.text_type(ex))
    outfile.write("\n")


@contextlib.contextmanager
def original_ld_library_path(env=None):
    # See: https://pyinstaller.readthedocs.io/en/stable/runtime-information.html
    # When running under pyinstaller, it will set an
    # LD_LIBRARY_PATH to ensure it prefers its bundled version of libs.
    # There are times where we don't want this behavior, for example when
    # running a separate subprocess.
    if env is None:
        env = os.environ

    value_to_put_back = env.get('LD_LIBRARY_PATH')
    # The first case is where a user has exported an LD_LIBRARY_PATH
    # in their env.  This will be mapped to LD_LIBRARY_PATH_ORIG.
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
    else:
        # Otherwise if they didn't set an LD_LIBRARY_PATH we just need
        # to make sure this value is unset.
        env.pop('LD_LIBRARY_PATH', None)
    try:
        yield
    finally:
        if value_to_put_back is not None:
            env['LD_LIBRARY_PATH'] = value_to_put_back


def dump_yaml_to_str(yaml, data):
    """Dump a Python object to a YAML-formatted string.

    :type yaml: ruamel.yaml.YAML
    :param yaml: An instance of ruamel.yaml.YAML.

    :type data: object
    :param data: A Python object that can be dumped to YAML.
    """
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


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
